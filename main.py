from fasthtml.common import *
from fastlite import database
from gen_graph import gen_graph
import uuid

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
        Script("""
            function toggleExamples() {
                const header = document.querySelector('.expandable-header');
                const content = document.querySelector('.expandable-content');
                header.classList.toggle('expanded');
                content.classList.toggle('expanded');
            }
        """)
    ]
)
BLANK_EXAMPLE = "examples..."
examples = {BLANK_EXAMPLE: ""}

# Load examples from the database
for example in db.t.examples():
    examples[example['name']] = example['dsl']

@rt("/convert")
def post(dsl:str): 
    if dsl:
        print(f"DSL has content: {dsl[:50]}")
    else:
        print("DSL is blank")
    return Pre(Code(gen_graph("graph", dsl))) if dsl else ''

def create_textarea(selection, dsl):
    print(f"create_textarea: {selection}")
    if selection != BLANK_EXAMPLE:
        dsl = examples[selection]
    return Textarea(dsl, placeholder='DSL text goes here', id="dsl", rows=10, hx_swap_oob='true'), Hidden(id="lastval", value=selection)

instructions = {
    "First line must contain the State class and the first node": ["START(StateClassName) => first_node"],
    "Nodes start on left margin": ["first_node => second_node"],
    "Conditions MUST be indented, and show the name of the conditional function": ["node_1", "  should_call_tool => tool_node", "  conditionY => node_3"],
    "The conditional function looks like this:": ["def should_call_tool(state: State) -> bool:", "  # your code here", "  return state['some_key'] == 'call_a_tool'"],
}

@rt("/toggle_syntax/{show}")
def get(show:bool):
    return Div(instructions, id="syntax", style="display: none;" if show else "display: block;")

def mk_show_hide(show, thing):
    return A(f"hide {thing}" if show else "show {thing}",
        get=f"/toggle_{thing}/" + ("False" if show else "True"),
        hx_target="#content{thing}", id="toggle_{thing}", hx_swap_oob="outerHTML",
        cls='uk-button uk-button-primary')

def Examples():
    return Div(
        H6("Examples", cls="expandable-header", onclick="toggleExamples()"),
        Div(
            *[A(name, cls="example-link", hx_get=f"/select_example/{name}", hx_target="#dsl") 
              for name in examples.keys() if name != BLANK_EXAMPLE],
            cls="expandable-content"
        ),
        cls="column left-column"
    )

def InstantAgent():
    return Div(
            H3("Instant Agent", style="font-style: italic;"),
            A("View README", hx_get='/about', target_id="about_lg_gen"),
            cls="header"
        )

@rt("/")
def get():
    return Div(
        InstantAgent(),
        Form(hx_post='/convert', target_id="lg_gen")(
            Div(
                Div(Examples(), cls='left-column'),
                Div(
                    Textarea(placeholder='DSL text goes here', id="dsl", rows=15),
                    Div(Ol(Li(Div(s), Pre("\n".join([line for line in code]))) for s,code in instructions.items())),
                    cls='middle-column'
                ),
                Div(
                    Button('Graph Builder Code', hx_post='/convert', target_id="lg_gen", style="display: inline-flex; align-items: center; justify-content: center; height: 30px; margin-top: 10px;"),
                    Pre(id="lg_gen"),
                    Div(id="about_lg_gen"),
                    cls='right-column'
                ),
                cls='main-container'
            ), 
        cls='page-container'
        )
    )

with open('README.md') as f: 
    about_md = f.read()

@rt("/about")
def get():
    return Div(about_md, cls='marked', style='text-align: left;')

@rt("/select_example/{name}")
def get(name:str):
    return examples[name].strip()


serve()