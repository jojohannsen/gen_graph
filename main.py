from fasthtml.common import *
from fastlite import database
from gen_graph import gen_graph, gen_nodes, gen_conditions, gen_state
import uuid
import re
# Create the database
db = database('data/gen_graph.db')

# Create tables if they don't exist
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
    ]
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
                hx_on="htmx:afterSettle: htmx.trigger('#dsl', 'input')",
                hx_swap_oob="true")
              for name in example_names],
              style="padding-top: 10px;"
        ),
        cls="column left-column",
        id="examples-list",
        hx_swap_oob="true"
    )

def TitleHeader():
    return Grid(
        H1("Agent Architectures", style="font-family: cursive; margin-bottom: 0;"),
        Div(
            A("View README", 
              hx_get='/toggle_readme', 
              hx_target="#readme_content",
              hx_swap="outerHTML",
              id="readme_link"),
            style="text-align: right;"
        ),
        cls="header"
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

@rt("/")
def get():
    first_example = next(iter(examples.keys()))
    return Main(
        TitleHeader(),
        Div(id="readme_content"),
        make_form(first_example), 
        cls='full-width'
    ), Link(rel="stylesheet", href="/static/styles.css")

with open('README.md') as f: 
    about_md = f.read()

def make_form(example_name:str):
    initial_dsl = examples[example_name]
    return Form()(
        Div(
            Div(Examples(example_name), cls='left-column'),
            Div(
                Div(
                    Textarea(initial_dsl, placeholder='DSL text goes here', id="dsl", rows=15),
                    Div(Ol(Li(Div(s), Pre("\n".join([line for line in code]))) for s,code in instructions.items())),
                    cls='middle-column'
                ),
                GeneratedCode(GRAPH_BUTTON, initial_dsl),
                style="display: flex; flex: 1;"
            ),
            cls='main-container'
        ), 
        cls='main-container'
    )

@rt("/hide_readme")
def get():
    main_content = make_form(examples[0])
    return Div(
        main_content,
        id="readme_content"
    ), A("View README", 
         hx_get='/toggle_readme', 
         hx_target="#readme_content",
         hx_swap="outerHTML",
         id="readme_link",
         hx_swap_oob="true")

@rt("/toggle_readme")
def get():
    return Div(
        Div(about_md, cls='marked', style='text-align: left;'),
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