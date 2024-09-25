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

function openTab(evt, tabName) {
    var i, tabContent, tabLinks;
    tabContent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabContent.length; i++) {
        tabContent[i].style.display = "none";
    }
    tabLinks = document.getElementsByClassName("tab");
    for (i = 0; i < tabLinks.length; i++) {
        tabLinks[i].className = tabLinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
    
    // Trigger HTMX request for the selected tab
    if (tabName === 'nodes-tab') {
        htmx.trigger('#nodes-tab', 'htmx:load');
    } else if (tabName === 'conditions-tab') {
        htmx.trigger('#conditions-tab', 'htmx:load');
    }
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

@rt("/get_nodes")
def get():
    # Here you would typically process the current DSL to extract node information
    # For now, we'll return a placeholder
    nodes = ["Node 1", "Node 2", "Node 3"]  # This should be dynamically generated based on the DSL
    return Ul(*[Li(node) for node in nodes])

@rt("/get_conditions")
def get():
    # Here you would typically process the current DSL to extract condition information
    # For now, we'll return a placeholder
    conditions = ["Condition 1", "Condition 2", "Condition 3"]  # This should be dynamically generated based on the DSL
    return Ul(*[Li(condition) for condition in conditions])

def TabContent():
    return Div(
        Div(
            Button('Graph', cls='tab active', onclick="openTab(event, 'graph-tab')"),
            Button('Nodes', cls='tab', onclick="openTab(event, 'nodes-tab')"),
            Button('Conditions', cls='tab', onclick="openTab(event, 'conditions-tab')"),
            cls='tab-container'
        ),
        Div(
            Div(
                Pre(id="lg_gen"),
                id='graph-tab',
                cls='tab-content active'
            ),
            Div(id='nodes-tab', cls='tab-content', hx_get='/get_nodes', hx_trigger='htmx:load'),
            Div(id='conditions-tab', cls='tab-content', hx_get='/get_conditions', hx_trigger='htmx:load'),
        ),
        cls='right-column'
    )

@rt("/")
def get():
    return Main(
        TitleHeader(),
        Div(id="readme_content"),
        Form(hx_post='/convert', target_id="lg_gen")(
            Div(
                Div(Examples(), cls='left-column'),
                Div(
                    Div(
                        Textarea(placeholder='DSL text goes here', id="dsl", rows=15),
                        Div(Ol(Li(Div(s), Pre("\n".join([line for line in code]))) for s,code in instructions.items())),
                        cls='middle-column'
                    ),
                    TabContent(),
                    style="display: flex; flex: 1;"
                ),
                cls='main-container'
            ), 
        cls='main-container'
        ), 
        cls='full-width'
    )

with open('README.md') as f: 
    about_md = f.read()

def make_form():
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
                cls='right-column'
            ),
            cls='main-container'
        ), 
        cls='main-container'
    )

@rt("/hide_readme")
def get():
    main_content = make_form()
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

@rt("/select_example/{name}")
def get(name:str):
    return examples[name].strip()


serve()