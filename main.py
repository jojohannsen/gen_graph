from fasthtml.common import *
from fastlite import database
from gen_graph import gen_graph, gen_nodes, gen_conditions, gen_state
import uuid
import re

# Read the README.md file, and set up the database
with open('README.md') as f: 
    about_md = f.read()

db = database('data/gen_graph.db')

def before(session):
    if 'sid' not in session:
        session['sid'] = str(uuid.uuid4())

app, rt = fast_app(
    db_file='data/gen_graph.db',
    hdrs=[
        picolink, 
        MarkdownJS(), 
        HighlightJS(),
        Link(rel="stylesheet", href="/static/styles.css"),
        Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css"),
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/mode/simple.min.js"),
    ],
    before=before  
)

# Function to load all architectures from the database
def load_architectures():
    architectures = {row['id']: row for row in db.t.architectures()}
    return dict(sorted(architectures.items(), key=lambda item: item[1]['name'].lower()))

# Load architectures from the database
architectures = load_architectures()

instructions = {
    "First line must contain the State class and the first node": ["START(StateClassName) => first_node"],
    "Nodes start on left margin": ["first_node => second_node"],
    "Conditions MUST be indented, and show the name of the conditional function": ["node_1", "  should_call_tool => tool_node", "  conditionY => node_3"],
    "The conditional function looks like this:": ["def should_call_tool(state: State) -> bool:", "  # your code here", "  return state['some_key'] == 'call_a_tool'"],
}

@rt("/toggle_syntax/{show}")
def get(show:bool):
    return Div(instructions, id="syntax", style="display: none;" if show else "display: block;")

@rt("/examples/{selected_example}")
def get(selected_example: str):
    return Examples(selected_example), Hidden(selected_example, id="architecture_id", hx_swap="outerHTML")

def remove_non_alphanumeric(input_string):
    return re.sub(r'[^a-zA-Z0-9]', '', input_string)

def Examples(selected_example=None):
    if selected_example is None:
        selected_example = next(iter(architectures.keys()))
    return Div(
        Hidden(selected_example, id="architecture_id", hx_swap="outerHTML"),
        Div(
            *[A(arch['name'], 
                id=f"example-link-{remove_non_alphanumeric(arch['name'])}",
                cls=f"example-link{' selected' if arch['id'] == selected_example else ''}", 
                hx_get=f"/architecture/{arch['id']}", 
                hx_target="#dsl",
                hx_trigger="click, keyup[key=='Enter']",
                hx_on="htmx:afterOnLoad: function() { if (typeof update_editor !== 'undefined') { setTimeout(update_editor, 100); } }",
              )
              for arch in architectures.values()],
              style="padding-top: 10px;"
        ),
        Script("if (typeof update_editor !== 'undefined') { setTimeout(update_editor, 100); }"),
        cls="column left-column",
        id="examples-list",
        hx_swap_oob="true"
    )

@rt("/toggle_readme")
def get(request: Request):
    is_visible = 'true' in request.query_params.get('visible', 'false')
    
    if is_visible:
        return A("View Project README", 
                 hx_get='/toggle_readme?visible=false', 
                 hx_target="#readme_content",
                 hx_swap="innerHTML",
                 hx_swap_oob="true", 
                 id="readme_toggle")
    else:
        return Div(
            Div(about_md, cls='marked', style='padding: 20px; text-align: left;'),
            A("Hide Project README", 
              hx_get='/toggle_readme?visible=true', 
              hx_target="#readme_content",
              hx_swap="innerHTML",
              hx_swap_oob="true", 
              id="readme_toggle")
        )

def TitleHeader():
    return Div(
        Grid(
            Div(
                H1("LangGraph Architectures", style="font-family: cursive; margin-bottom: 0; display: inline;"),
                style="display: flex; align-items: center;"
            ),
            A("View README", 
              hx_get='/toggle_readme', 
              hx_target="#readme_content",
              hx_swap="innerHTML",
              id="readme_toggle",
              hx_swap_oob="true"),
            cls="header"
        ),
        Div(id="readme_content"),
        cls="header-container"
    )

@rt("/get_readme")
def post(dsl: str, architecture_id:str, simulation_code: str = "false"):
    return GeneratedCode(README_BUTTON, dsl, architecture_id, simulation_code == "on", conditions_content=None)

@rt("/get_state")
def post(dsl: str, architecture_id: str, simulation_code: str = "false"):
    return GeneratedCode(STATE_BUTTON, dsl, architecture_id, simulation_code == "on", conditions_content=None)

@rt("/get_graph")
def post(dsl: str, architecture_id:str, simulation_code: str = "false"):
    return GeneratedCode(GRAPH_BUTTON, dsl, architecture_id, simulation_code == "on", conditions_content=None)

import ast

def extract_global_variables(func_code):
    class GlobalVarVisitor(ast.NodeVisitor):
        def __init__(self):
            self.global_vars = set()
            self.local_vars = set()

        def visit_FunctionDef(self, node):
            # Add function arguments to local variables
            self.local_vars.update(arg.arg for arg in node.args.args)
            # Visit the function body
            for item in node.body:
                self.visit(item)

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load) and node.id not in self.local_vars:
                self.global_vars.add(node.id)
            elif isinstance(node.ctx, ast.Store):
                self.local_vars.add(node.id)

        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.local_vars.add(target.id)
            self.visit(node.value)

        def visit_ListComp(self, node):
            # Save the current state of local_vars
            old_local_vars = self.local_vars.copy()
            
            # Add the comprehension variables to local_vars
            for generator in node.generators:
                if isinstance(generator.target, ast.Name):
                    self.local_vars.add(generator.target.id)
            
            # Visit the comprehension elements
            self.visit(node.elt)
            
            # Restore the old state of local_vars
            self.local_vars = old_local_vars

    tree = ast.parse(func_code)
    visitor = GlobalVarVisitor()
    visitor.visit(tree)
    
    # Remove built-in function names
    builtins = set(dir(__builtins__))
    global_vars = visitor.global_vars - builtins
    
    return sorted(list(global_vars))

def format_undefined_lines(global_vars, line_length=40):
    lines = []
    current_line = "# UNDEFINED: "
    
    for var in global_vars:
        if len(current_line) + len(var) + 2 > line_length:  # +2 for comma and space
            lines.append(current_line.strip(", "))  # Remove trailing comma and space
            current_line = "# UNDEFINED: "
        
        current_line += var + ", "
    
    if current_line.strip(", "):  # Append the last line if it's not empty
        lines.append(current_line.strip(", "))
    
    return lines


@rt("/get_nodes")
def post(dsl:str, architecture_id:str, simulation_code: str = "off"):
    arch = architectures[int(architecture_id)]
    print(arch)
    if simulation_code == "on":
        nodes_content = gen_nodes(dsl).strip()
    else:
        nodes_content = arch['nodes'].strip()
    global_vars = extract_global_variables(nodes_content)
    
    if len(global_vars) > 0:
        undefined_lines = format_undefined_lines(global_vars, line_length=60)
        nodes_content = "\n".join(undefined_lines) + "\n" + nodes_content
    return GeneratedCode(NODES_BUTTON, 
                         dsl, 
                         architecture_id, 
                         simulation_code == "on", 
                         nodes_content=nodes_content,
                         conditions_content=None)

@rt("/get_conditions")
def post(dsl:str, architecture_id:str, simulation_code: str = "false"):
    arch = architectures[int(architecture_id)]
    if simulation_code == "on":
        conditions_content = gen_conditions(dsl).strip()
    else:
        conditions_content = arch['conditions'].strip()
    return GeneratedCode(CONDITIONS_BUTTON, dsl, architecture_id, simulation_code == "on", conditions_content=conditions_content)

README_BUTTON = 'README'
STATE_BUTTON = 'State'
NODES_BUTTON = 'Nodes'
CONDITIONS_BUTTON = 'Conditions'
GRAPH_BUTTON = 'Graph'

def CodeGenerationButtons(active_button:str=None, architecture_id:str=None, simulation_code:bool=False):
    return Div(  
        Button(README_BUTTON, id="readme_button", hx_post=f'/get_readme', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == README_BUTTON else ""}'),        
        Button(STATE_BUTTON, hx_post='/get_state', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == STATE_BUTTON else ""}'),
        Button(NODES_BUTTON, hx_post='/get_nodes', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == NODES_BUTTON else ""}'),
        Button(CONDITIONS_BUTTON, hx_post='/get_conditions', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == CONDITIONS_BUTTON else ""}'),
        Button(GRAPH_BUTTON, hx_post='/get_graph', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == GRAPH_BUTTON else ""}'),
        Span(style="flex-grow: 1;"),  # This will push the checkbox to the right
        Label(
            Input(type="checkbox", name="simulation_code", id="simulation_code_checkbox",
                  hx_post=f'/get_{active_button.lower()}',
                  hx_target='#code-generation-ui',
                  hx_swap='outerHTML',
                  hx_include='#dsl,#architecture_id',
                  checked=simulation_code),
            Span("Simulation Code", style="font-size: 0.8em; font-style: italic; color: #999;"),
            style="display: flex; align-items: center;"
        ),
        id='code-generation-buttons',
        cls='toggle-buttons',
        style="display: flex; justify-content: space-between; align-items: center;"
    )

def mk_name(name:str):
    # replace dashes and spaces with underscores, make it all lowercase
    return name.replace('-', '_').replace(' ', '_').replace('(', '').replace(')', '').lower()

def CodeGenerationContent(
        active_button:str=None, 
        dsl:str=None, 
        architecture_id:str=None, 
        simulation_code:bool=False,
        nodes_content:str=None,
        conditions_content:str=None
        ):
    arch = architectures[int(architecture_id)]
    arch_name = mk_name(arch['name']) or "graph"
    if active_button == README_BUTTON:
        if arch:
            arch_md = arch['readme']
        else:
            arch_md = "README not available for this architecture."
        arch_div = Div(arch_md, cls='marked', style='padding: 20px; text-align: left;'),
    else:
        arch_div = ''
    
    arch_readme_div = Div(arch_div, id="architecture-readme", cls=f'tab-content{" active" if active_button == README_BUTTON else ""}')
    state_content = gen_state(dsl).strip() if simulation_code else arch['state'].strip()
    state_pre = Pre(Code(state_content), id="state-code") if active_button == STATE_BUTTON else Pre(id="state-code")
    state_div = Div(state_pre, cls=f'tab-content{" active" if active_button == STATE_BUTTON else ""}')
    nodes_pre = Pre(Code(nodes_content), id="nodes-code") if active_button == NODES_BUTTON else Pre(id="nodes-code")
    nodes_div = Div(nodes_pre, cls=f'tab-content{" active" if active_button == NODES_BUTTON else ""}')
    conditions_pre = Pre(Code(conditions_content), id="conditions-code") if active_button == CONDITIONS_BUTTON else Pre(id="conditions-code")
    conditions_div = Div(conditions_pre, cls=f'tab-content{" active" if active_button == CONDITIONS_BUTTON else ""}')
    graph_pre = Pre(Code(gen_graph(arch_name, dsl).strip()), id="graph-code") if active_button == GRAPH_BUTTON else Pre(id="graph-code")
    graph_div = Div(graph_pre, cls=f'tab-content{" active" if active_button == GRAPH_BUTTON else ""}')
    return Div(
        arch_readme_div,
        state_div,
        nodes_div,
        conditions_div,
        graph_div,
        cls='toggle-buttons'
    )

def GeneratedCode(active_button:str=None, dsl:str=None, architecture_id:str=None, simulation_code:bool=False, nodes_content:str=None, conditions_content:str=None):
    return Div(
        CodeGenerationButtons(active_button, architecture_id, simulation_code),
        CodeGenerationContent(active_button, dsl, architecture_id, simulation_code, nodes_content, conditions_content),
        cls='right-column',
        id='code-generation-ui',
    )

def TheWholeEnchilada(architecture_id:str):
    return Div(
        Div(id="readme_content"),
        make_form(architecture_id), 
        cls='full-width',
        id='the-whole-enchilada',
        hx_swap_oob='true'
    )

@rt("/")
def get():
    first_architecture_id = next(iter(architectures.keys()))
    return Main(
        TitleHeader(),
        Div(
            TheWholeEnchilada(first_architecture_id),
            id="main_content"
        ),
        cls='full-width',
    )

def make_form(example_id:str):
    print(f"make_form: example_id={example_id}")
    initial_dsl = architectures[example_id]['graph_spec']
    return Form()(
        Div(
            Div(Examples(example_id), cls='left-column'),
            Div(
                Div(
                    Textarea(initial_dsl, placeholder='DSL text goes here', id="dsl", rows=25,cls="code-editor"),
                    #Div(Ol(Li(Div(s), Pre("\n".join([line for line in code]))) for s,code in instructions.items())),
                    cls='middle-column'
                ),
                GeneratedCode(README_BUTTON, initial_dsl, example_id),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/mode/simple.min.js"),
                Script(src="/static/script.js", defer=True),
                style="display: flex; flex: 1;"
            ),
            cls='main-container'
        ), 
        cls='main-container'
    )

@rt("/hide_readme")
def get():
    return redirect("/")

@rt("/view_readme")
def get():
    return Div(
        Div(about_md, cls='marked', style='padding: 20px; text-align: left;'),
        id="readme_content"
    ), A("Hide README", 
         hx_get='/hide_readme', 
         hx_target="#readme_content",
         hx_swap="outerHTML",
         id="readme_link",
         hx_swap_oob="true")

@rt("/architecture/{arch_id}")
def get(arch_id:int):
    arch = architectures.get(arch_id)
    if arch is None:
        raise HTTPException(status_code=404, detail="Architecture not found")
    return arch['graph_spec'].strip(), Examples(arch_id)

serve()