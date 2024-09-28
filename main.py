from fasthtml.common import *
from fastlite import database
from gen_graph import gen_graph, gen_nodes, gen_conditions, gen_state
import uuid
import re

# Read the README.md file, and set up the database
with open('README.md') as f: 
    about_md = f.read()

db = database('data/gen_graph.db')
if 'examples' not in db.t:
    db.t.examples.create(id=str, name=str, dsl=str, pk='id')

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

examples = {}

# Load examples from the database
for example in db.t.examples():
    examples[example['name']] = example['dsl']

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
    return Examples(selected_example)

def remove_non_alphanumeric(input_string):
    return re.sub(r'[^a-zA-Z0-9]', '', input_string)

def Examples(selected_example=None):
    example_names = list(examples.keys())
    if selected_example is None:
        selected_example = next(name for name in example_names)
    print(f"Examples: selected_example={selected_example}")
    print(f"Examples: example_names={example_names}")
    return Div(
        Div(
            *[A(name, 
                id=f"example-link-{remove_non_alphanumeric(name)}",
                cls=f"example-link{' selected' if name == selected_example else ''}", 
                hx_get=f"/architecture/{name}", 
                hx_target="#dsl",
                hx_trigger="click, keyup[key=='Enter']",
                hx_on="htmx:afterOnLoad: function() { if (typeof update_editor !== 'undefined') { setTimeout(update_editor, 100); } }",
              )
              for name in example_names],
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
        return A("View README", 
                 hx_get='/toggle_readme?visible=false', 
                 hx_target="#readme_content",
                 hx_swap="innerHTML",
                 hx_swap_oob="true", 
                 id="readme_toggle")
    else:
        return Div(
            Div(about_md, cls='marked', style='padding: 20px; text-align: left;'),
            A("Hide README", 
              hx_get='/toggle_readme?visible=true', 
              hx_target="#readme_content",
              hx_swap="innerHTML",
              hx_swap_oob="true", 
              id="readme_toggle")
        )

def TitleHeader():
    return Div(
        Grid(
            H1("Agent Architectures", style="font-family: cursive; margin-bottom: 0;"),
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

@rt("/get_state")
def post(dsl: str):
    print(f"GET_STATE: post")
    if dsl:
        print(f"DSL has content: {dsl[:50]}")
    else:
        print("DSL is blank")
    return GeneratedCode(STATE_BUTTON, dsl)

@rt("/get_graph")
def post(dsl: str):
    print(f"GET_GRAPH: post")
    if dsl:
        print(f"DSL has content: {dsl[:50]}")
    else:
        print("DSL is blank")
    
    return GeneratedCode(GRAPH_BUTTON, dsl)
    

@rt("/get_nodes")
def post(dsl:str):
    return GeneratedCode(NODES_BUTTON, dsl)

@rt("/get_conditions")
def post(dsl:str):
    return GeneratedCode(CONDITIONS_BUTTON, dsl)

STATE_BUTTON = 'State'
GRAPH_BUTTON = 'Graph'
NODES_BUTTON = 'Nodes'
CONDITIONS_BUTTON = 'Conditions'

def CodeGenerationButtons(active_button:str=None):
    print(f"CodeGenerationButtons: active_button={active_button}")
    return Div(
        Button(STATE_BUTTON, hx_post='/get_state', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == STATE_BUTTON else ""}'),
        Button(GRAPH_BUTTON, hx_post='/get_graph', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == GRAPH_BUTTON else ""}'),
        Button(NODES_BUTTON, hx_post='/get_nodes', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == NODES_BUTTON else ""}'),
        Button(CONDITIONS_BUTTON, hx_post='/get_conditions', target_id='code-generation-ui', hx_swap='outerHTML',
            cls=f'code-generation-button{" active" if active_button == CONDITIONS_BUTTON else ""}'),
        id='code-generation-buttons',
        cls='toggle-buttons'
    )

def CodeGenerationContent(active_button:str=None, dsl:str=None):
    print(f"CodeGenerationContent: active_button={active_button}")
    state_pre = Pre(Code(gen_state(dsl).strip()), id="state-code") if active_button == STATE_BUTTON else Pre(id="state-code")
    state_div = Div(state_pre, cls=f'tab-content{" active" if active_button == STATE_BUTTON else ""}')
    graph_pre = Pre(Code(gen_graph("graph", dsl).strip()), id="graph-code") if active_button == GRAPH_BUTTON else Pre(id="graph-code")
    graph_div = Div(graph_pre, cls=f'tab-content{" active" if active_button == GRAPH_BUTTON else ""}')
    nodes_pre = Pre(Code(gen_nodes(dsl).strip()), id="nodes-code") if active_button == NODES_BUTTON else Pre(id="nodes-code")
    nodes_div = Div(nodes_pre, cls=f'tab-content{" active" if active_button == NODES_BUTTON else ""}')
    conditions_pre = Pre(Code(gen_conditions(dsl).strip()), id="conditions-code") if active_button == CONDITIONS_BUTTON else Pre(id="conditions-code")
    conditions_div = Div(conditions_pre, cls=f'tab-content{" active" if active_button == CONDITIONS_BUTTON else ""}')
    return Div(
        state_div,
        graph_div,
        nodes_div,
        conditions_div,
        cls='toggle-buttons'
    )

def GeneratedCode(active_button:str=None, dsl:str=None):
    return Div(
        CodeGenerationButtons(active_button),
        CodeGenerationContent(active_button, dsl),
        cls='right-column',
        id='code-generation-ui',
    )

def TheWholeEnchilada(example_name:str):
    return Div(
        Div(id="readme_content"),
        make_form(example_name), 
        cls='full-width',
        id='the-whole-enchilada',
        hx_swap_oob='true'
    )

@rt("/")
def get():
    first_example = next(iter(examples.keys()))
    return Main(
        TitleHeader(),
        TheWholeEnchilada(first_example),
        cls='full-width',
    )


def make_form(example_name:str):
    initial_dsl = examples[example_name]
    return Form()(
        Div(
            Div(Examples(example_name), cls='left-column'),
            Div(
                Div(
                    Textarea(initial_dsl, placeholder='DSL text goes here', id="dsl", rows=15, cls="code-editor"),
                    Div(Ol(Li(Div(s), Pre("\n".join([line for line in code]))) for s,code in instructions.items())),
                    cls='middle-column'
                ),
                GeneratedCode(GRAPH_BUTTON, initial_dsl),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/mode/simple.min.js"),
                Script(src="/static/script.js"),
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

@rt("/architecture/{name}")
def get(name:str):
    return examples[name].strip(), Examples(name)

serve()