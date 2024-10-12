from fasthtml.common import *
from fastlite import database
from gen_graph import gen_graph, gen_nodes, gen_conditions, gen_state
from code_utils.code_snippet_analyzer import CodeSnippetAnalyzer
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
def load_architectures() -> dict:
    architectures = {row['id']: row for row in db.t.architectures()}
    return dict(sorted(architectures.items(), key=lambda item: item[1]['name'].lower()))

# Load architectures from the database
architectures = load_architectures()

BUTTON_TYPES = ['README', 'STATE', 'NODES', 'CONDITIONS', 'GRAPH', 'TOOLS', 'MODELS']

def sanitize_filename(name: str) -> str:
    name = name.lower().replace(' ', '-').replace(',', '').replace('(', '').replace(')', '')
    return re.sub(r'[^a-z0-9-]', '', name)

def Examples(selected_example: str = None):
    if selected_example is None:
        selected_example = next(iter(architectures.keys()))
    return Div(
        Hidden(selected_example, id="architecture_id", hx_swap="outerHTML"),
        Div(
            *[Div(
                Div(
                    A(arch['name'], 
                      id=f"example-link-{sanitize_filename(arch['name'])}",
                      cls=f"example-link{' selected' if arch['id'] == selected_example else ''}", 
                      hx_get=f"/architecture/{arch['id']}", 
                      hx_target="#dsl",
                      hx_trigger="click, keyup[key=='Enter']",
                      hx_on="htmx:afterOnLoad: function() { if (typeof update_editor !== 'undefined') { setTimeout(update_editor, 100); } }",
                    ),
                ),
                Div(
                    A(f"Download {sanitize_filename(arch['name'])}.ipynb", 
                      href=f"/download/{sanitize_filename(arch['name'])}.ipynb",
                      cls="download-notebook-link",
                      style="font-size: 0.8em; display: none;" if arch['id'] != selected_example else "font-size: 0.8em;"),
                    style="margin-left: 20px; margin-top: 5px;"
                ),
                style="margin-bottom: 10px;"
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
                Span("LangGraph Architectures", 
                     style="font-family: cursive; margin-bottom: 0; font-size: 1.4rem; color: #888; margin-right: 1rem;"),
                Span(id="current-architecture", 
                     style="font-weight: bold;"),
                style="display: flex; align-items: baseline;"
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

def mk_name(name:str):
    return name.replace('-', '_').replace(',', '').replace(' ', '_').replace('(', '').replace(')', '').lower()

def generate_code(architecture_id: int, button_type: str, simulation: bool) -> str:
    arch = architectures[architecture_id]
    if button_type == 'GRAPH':
        return gen_graph(mk_name(arch['name']), arch['graph_spec']).strip()
    elif simulation:
        simulation_functions = {
            'STATE': gen_state,
            'NODES': gen_nodes,
            'CONDITIONS': gen_conditions,
            'TOOLS': lambda _: "# Tools simulation not implemented",
            'MODELS': lambda _: "# Models simulation not implemented"
        }
        return simulation_functions[button_type](arch['graph_spec']).strip()
    else:
        return arch[button_type.lower()].strip()


def CodeGenerationButtons(active_button: str, architecture_id: str, simulation: bool):
    button_labels = {
        'README': 'Readme',
        'STATE': 'State',
        'NODES': 'Nodes',
        'CONDITIONS': 'Conditions',
        'GRAPH': 'Graph',
        'TOOLS': 'Tools',
        'MODELS': 'Models'
    }
    return Div(  
        *[Button(button_labels[btn], id=f"{btn.lower()}_button", 
                 hx_post=f'/get_code/{btn}', 
                 target_id='code-generation-ui', 
                 hx_swap='outerHTML',
                 cls=f'code-generation-button{" active" if active_button == btn else ""}{" italic" if btn in ["TOOLS", "MODELS"] else ""}')
          for btn in BUTTON_TYPES],
        Span(style="flex-grow: 1;"),
        Label(
            Input(type="checkbox", name="simulation_code", id="simulation_code_checkbox",
                  hx_post=f'/get_code/{active_button}',
                  hx_target='#code-generation-ui',
                  hx_swap='outerHTML',
                  hx_include='#dsl,#architecture_id',
                  checked=simulation,
                  disabled=active_button == 'GRAPH'),
            Span("Simulation Code", style="font-size: 0.8em; font-style: italic; color: #999;"),
            style="display: flex; align-items: center;"
        ),
        id='code-generation-buttons',
        cls='toggle-buttons',
        style="display: flex; justify-content: space-between; align-items: center;"
    )

def CodeGenerationContent(active_button: str, architecture_id: str, simulation: bool, content: str):
    if active_button == 'README':
        return Div(Div(content, cls='marked', style='padding: 20px; text-align: left;'),
                   id="architecture-readme", 
                   cls=f'tab-content active')
    else:
        return Div(Pre(Code(content), id=f"{active_button.lower()}-code"),
                   cls=f'tab-content active')


def format_analysis_summary(summary):
    defined, undefined, defined_elsewhere = summary
    messages = []
    if defined:
        messages.append(f"Defined variables: {', '.join(defined)}")
    if undefined:
        messages.append(f"Undefined variables: {', '.join(undefined)}")
    if defined_elsewhere:
        messages.append(f"Variables defined elsewhere: {', '.join(defined_elsewhere)}")
    return messages


@rt("/get_code/{button_type}")
def post(button_type: str, dsl: str, architecture_id: str, simulation_code: str = "false"):
    simulation = simulation_code == "on" and button_type != 'GRAPH'
    code = generate_code(int(architecture_id), button_type.upper(), simulation)
    
    # Get the analysis for this architecture
    analyzer = analyze_architecture_code(int(architecture_id))
    
    # Get the summary for this specific snippet
    snippet_name = button_type.lower()
    if simulation and snippet_name in ['state', 'nodes', 'conditions']:
        snippet_name = f"{snippet_name}_simulation"
    summary = analyzer.get_snippet_summary(snippet_name)
    
    analysis_messages = format_analysis_summary(summary) if summary else ["No analysis available for this snippet."]
    
    return GeneratedCode(button_type.upper(), dsl, architecture_id, simulation, code, analysis_messages)


# ... existing code ...

def AnalysisMessages(analysis_messages: list):
    def format_message(message: str):
        if message.startswith("Defined variables:"):
            return "Defined: " + message.split(": ", 1)[1], "success"
        elif message.startswith("Undefined variables:"):
            return "Undefined: " + message.split(": ", 1)[1], "error"
        elif message.startswith("Variables defined elsewhere:"):
            return "Defined elsewhere: " + message.split(": ", 1)[1], "info"
        else:
            return message, "info"

    return Div(
        *[Div(formatted_message, cls=f"message {message_type}")
          for message in analysis_messages
          for formatted_message, message_type in [format_message(message)] if message_type == "error"],
        cls="message-area",
        style="margin-top: 20px;"
    )

def GeneratedCode(active_button: str, dsl: str, architecture_id: str, simulation: bool, content: str, analysis_messages: list):
    return Div(
        CodeGenerationButtons(active_button, architecture_id, simulation),
        CodeGenerationContent(active_button, architecture_id, simulation, content),
        AnalysisMessages(analysis_messages),
        cls='right-column',
        id='code-generation-ui',
    )


def TheWholeEnchilada(architecture_id: str):
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
    first_architecture_name = architectures[first_architecture_id]['name']
    return Main(
        TitleHeader(),
        Div(
            TheWholeEnchilada(first_architecture_id),
            id="main_content"
        ),
        Script(f"document.getElementById('current-architecture').textContent = '{first_architecture_name}';"),
        cls='full-width',
    )

def make_form(example_id: str):
    initial_dsl = architectures[int(example_id)]['graph_spec']
    
    # Analyze the initial architecture
    analyzer = analyze_architecture_code(int(example_id))
    readme_summary = analyzer.get_snippet_summary('readme') or (set(), set(), set())
    analysis_messages = format_analysis_summary(readme_summary)
    
    return Form()(
        Div(
            Div(Examples(example_id), cls='left-column'),
            Div(
                Div(
                    Textarea(initial_dsl, placeholder='DSL text goes here', id="dsl", rows=25, cls="code-editor"),
                    cls='middle-column'
                ),
                GeneratedCode('README', initial_dsl, example_id, False, architectures[int(example_id)]['readme'], analysis_messages),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/mode/simple.min.js"),
                Script(src="/static/script.js", defer=True),
                style="display: flex; flex: 1;"
            ),
            cls='main-container'
        ), 
        cls='main-container'
    )
#aa
@rt("/get_code/{button_type}")
def post(button_type: str, dsl: str, architecture_id: str, simulation_code: str = "false"):
    simulation = simulation_code == "on" and button_type != 'GRAPH'
    code = generate_code(int(architecture_id), button_type.upper(), simulation)
    
    # Get the analysis for this architecture
    analyzer = analyze_architecture_code(int(architecture_id))
    
    # Get the summary for this specific snippet
    snippet_name = button_type.lower()
    if simulation and snippet_name in ['state', 'nodes', 'conditions']:
        snippet_name = f"{snippet_name}_simulation"
    summary = analyzer.get_snippet_summary(snippet_name)
    
    analysis_messages = format_analysis_summary(summary) if summary else ["No analysis available for this snippet."]
    
    return GeneratedCode(button_type.upper(), dsl, architecture_id, simulation, code, analysis_messages)


@rt("/architecture/{arch_id}")
def get(arch_id: int):
    arch = architectures.get(arch_id)
    if arch is None:
        raise HTTPException(status_code=404, detail="Architecture not found")
    return (
        arch['graph_spec'].strip(), 
        Examples(arch_id),
        Script(f"""
            var currentArch = document.getElementById('current-architecture');
            currentArch.textContent = '{arch['name']}';
            currentArch.style.opacity = '0';
            setTimeout(() => {{
                currentArch.style.opacity = '1';
            }}, 50);
        """)
    )   

@rt("/download/{notebook_name}")
def get(notebook_name: str):
    return PlainTextResponse(f"This would be the notebook for {notebook_name}")

def analyze_architecture_code(architecture_id: int) -> CodeSnippetAnalyzer:
    arch = architectures[architecture_id]
    
    if arch is None:
        raise ValueError(f"Architecture with id {architecture_id} not found")

    analyzer = CodeSnippetAnalyzer()

    # Analyze each code snippet
    for field in ['state', 'nodes', 'conditions', 'models', 'tools']:
        code = arch.get(field, '').strip()
        if code:
            analyzer.add_snippet(field, code)

    # Generate and analyze graph code
    graph_code = gen_graph(mk_name(arch['name']), arch['graph_spec']).strip()
    analyzer.add_snippet('graph', graph_code)

    # Perform analysis on all snippets
    analyzer.analyze_all_snippets()

    return analyzer

serve()
