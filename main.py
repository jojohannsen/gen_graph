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
    session['title'] = "GraphDSL"  # Add this line to set the title


app, rt = fast_app(
    db_file='data/gen_graph.db',
    hdrs=[
        picolink, 
        MarkdownJS(), 
        HighlightJS(),
        Link(rel="stylesheet", href="/static/styles.css"),
        Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css"),
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"),
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/python/python.min.js"),
        Script("""
        var BASE_URL = window.location.origin;
        """),
        Script("""
        document.addEventListener('DOMContentLoaded', function() {
            console.log('CodeMirror version:', CodeMirror.version);
            console.log('Python mode loaded:', typeof CodeMirror.modes.python !== 'undefined');
            if (typeof CodeMirror.modes.python === 'undefined') {
                console.error('Python mode not loaded. Attempting to load it manually.');
                var script = document.createElement('script');
                script.src = "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/python/python.min.js";
                document.head.appendChild(script);
                script.onload = function() {
                    console.log('Python mode loaded manually:', typeof CodeMirror.modes.python !== 'undefined');
                };
            }
        });
        """),
        Script(src="/static/script.js", defer=True),
    ],
    before=before  
)
# Function to load all architectures from the database
def load_architectures() -> dict:
    architectures = {row['id']: row for row in db.t.arch()}
    return dict(sorted(architectures.items(), key=lambda item: item[1]['name'].lower()))

def load_imports():
    imports_dict = {}
    for import_item in db.t.imports():
        imports_dict[import_item['what']] = import_item['frm']
    return imports_dict

# Example usage of load_imports
imports_dict = load_imports()
architectures = load_architectures()

BUTTON_TYPES = ['README', 'STATE', 'NODES', 'CONDITIONS', 'GRAPH', 'TOOLS', 'DATA', 'LLMS']

def sanitize_filename(name: str) -> str:
    name = name.lower().replace(' ', '-').replace(',', '').replace('(', '').replace(')', '')
    return re.sub(r'[^a-z0-9-]', '', name)

def Examples(selected_example: str = None):
    if selected_example is None:
        selected_example = next(iter(architectures.keys()))
    return Div(
        Hidden(selected_example, id="architecture_id", name="architecture_id", hx_swap="outerHTML"),
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
                style="margin-bottom: 10px;"
              )
              for arch in architectures.values()],
            style="padding-top: 10px;"
        ),
        Script("""
        if (typeof update_editor !== 'undefined') { 
            setTimeout(update_editor, 100); 
        }
        document.getElementById('dsl').addEventListener('input', function() {
            htmx.trigger('#code-generation-ui', 'refreshContent');
        });
        """),
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
    if button_type == 'README':
        return arch['readme'].strip()
    if button_type == 'GRAPH':
        return gen_graph(mk_name(arch['name']), arch['graph_spec']).strip()
    elif simulation:
        simulation_functions = {
            'STATE': gen_state,
            'NODES': gen_nodes,
            'CONDITIONS': gen_conditions,
            'TOOLS': lambda _: arch['tools'].strip(),  # Display the same content in simulation mode
            'DATA': lambda _: arch['data'].strip(),  # Display the 'data' field content
            'LLMS': lambda _: "# LLMs simulation not implemented"
        }
        return simulation_functions[button_type](arch['graph_spec']).strip()
    else:
        return arch[button_type.lower()].strip()


def CodeGenerationButtons(active_button: str, architecture_id: str, simulation: bool):
    button_labels = {
        'README': 'README',
        'STATE': 'State',
        'NODES': 'Nodes',
        'CONDITIONS': 'Conditions',
        'GRAPH': 'Graph',
        'TOOLS': 'Tools',
        'DATA': 'Data',  # Added this line
        'LLMS': 'LLMs'
    }
    
    return Div(  
        *[Button(button_labels[btn], id=f"{btn.lower()}_button", 
                 hx_post=f'/get_code/{btn}', 
                 target_id='code-generation-ui', 
                 hx_swap='outerHTML',
                 hx_trigger="click", # why were these here??, refreshContent from:#code-generation-ui, editorReady",
                 hx_include="#dsl",
                 cls=f'code-generation-button{" active" if active_button == btn else ""}{" italic" if btn in ["TOOLS", "DATA", "LLMS"] else ""}')
          for btn in BUTTON_TYPES],
        Span(style="flex-grow: 1;"),
        Label(
            Input(type="checkbox", name="simulation_code", id="simulation_code_checkbox",
                  hx_post=f'/get_code/{active_button}',
                  hx_target='#code-generation-ui',
                  hx_swap='outerHTML',
                  hx_include='#dsl,#architecture_id',
                  hx_trigger="change, refreshContent from:#code-generation-ui",
                  checked=simulation,
                  disabled=active_button == 'GRAPH'),
            Span("Simulation Code", style="font-size: 0.8em; font-style: italic; color: #999;"),
            style="display: flex; align-items: center;"
        ),
        id='code-generation-buttons',
        cls='toggle-buttons',
        style="display: flex; justify-content: space-between; align-items: center;"
    )


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


def AnalysisMessages(analysis_messages: list):
    def format_message(message: str):
        if message.startswith("Defined variables:"):
            return "Defines: " + message.split(": ", 1)[1], "success"
        elif message.startswith("Undefined variables:"):
            return "Undefined: " + message.split(": ", 1)[1], "error"
        elif message.startswith("Variables defined elsewhere:"):
            return "Defined elsewhere: " + message.split(": ", 1)[1], "info"
        else:
            return message, "info"

    return Div(
        *[Div(formatted_message, cls=f"message {message_type}")
          for message in analysis_messages
          for formatted_message, message_type in [format_message(message)]],# if message_type == "error"],
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
def get(session):
    first_architecture_id = next(iter(architectures.keys()))
    first_architecture_name = architectures[first_architecture_id]['name']
    return Main(
        Title(session.get('title', 'GraphDSL')),  # Use the title from the session
        TitleHeader(),
        Div(
            TheWholeEnchilada(first_architecture_id),
            id="main_content"
        ),
        Script(f"document.getElementById('current-architecture').textContent = '{first_architecture_name}';"),
        cls='full-width',
    )



def remove_extra_blank_lines_oneline(lines):
    lines = lines.split("\n")
    return "\n".join(re.sub(r'\n\s*\n', '\n\n', '\n'.join(lines)).split('\n'))

@rt("/debug_dsl")
def get():
    return """
    <script>
        var dslContent = document.getElementById('dsl').value;
        console.log('Current DSL content:', dslContent);
        alert('Current DSL content (check console for full content): ' + dslContent.substring(0, 100) + '...');
    </script>
    """

# ... (previous imports and code remain the same)

# ... (previous imports and code remain the same)

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
                    Textarea(initial_dsl, placeholder='DSL text goes here', id="dsl", name="dsl", rows=25, cls="code-editor"),
                    cls='middle-column'
                ),
                GeneratedCode('README', initial_dsl, example_id, False, architectures[int(example_id)]['readme'], analysis_messages),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js"),
                Script(src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/addon/mode/simple.min.js"),
                Script(src="/static/script.js", defer=True),
                Script("""
                    document.body.addEventListener('htmx:configRequest', (event) => {
                        ensureEditorInitialized();
                        if (window.editor) {
                            event.detail.parameters['dsl'] = window.editor.getValue();
                        } else {
                            console.log('Editor not found, falling back to textarea value');
                            event.detail.parameters['dsl'] = document.getElementById('dsl').value;
                        }
                        // Include the architecture_id in the request
                        event.detail.parameters['architecture_id'] = document.getElementById('architecture_id').value;
                    });

                    // Wait for the editor to be ready before allowing HTMX requests
                    function waitForEditor() {
                        if (window.editor) {
                            htmx.trigger('#code-generation-ui', 'editorReady');
                        } else {
                            setTimeout(waitForEditor, 100);
                        }
                    }
                    waitForEditor();
                """),
                style="display: flex; flex: 1;"
            ),
            cls='main-container'
        ), 
        cls='main-container'
    )

def CodeGenerationContent(active_button: str, architecture_id: str, simulation: bool, content: str):
    if active_button == 'README':
        return Div(Div(content, cls='marked', style='padding: 20px; text-align: left;'),
                   id="architecture-readme", 
                   cls=f'tab-content active')
    elif active_button in ['STATE', 'NODES', 'CONDITIONS', 'TOOLS', 'DATA', 'LLMS']:
        return Div(
            Textarea(content, id=f"{active_button.lower()}-code-editor", name=f"{active_button.lower()}-code-editor", cls="code-editor"),
            cls=f'tab-content active'
        )
    else:
        return Div(Pre(Code(content), id=f"{active_button.lower()}-code"),
                   cls=f'tab-content active')

@rt("/get_code/{button_type}")
def post(button_type: str, dsl: str, architecture_id: str, simulation_code: str = "false"):
    simulation = simulation_code == "on" and button_type != 'GRAPH'
    
    # Update the architecture's graph_spec with the new DSL
    architectures[int(architecture_id)]['graph_spec'] = dsl
    
    code = generate_code(int(architecture_id), button_type.upper(), simulation)
    
    # Get the analysis for this architecture
    analyzer = analyze_architecture_code(int(architecture_id))
    
    # Get the summary for this specific snippet
    snippet_name = button_type.lower()
    if simulation and snippet_name in ['state', 'nodes', 'conditions']:
        snippet_name = f"{snippet_name}_simulation"
    summary = analyzer.get_snippet_summary(snippet_name)
    
    if summary:
        defined, undefined, defined_elsewhere = summary
        imported_vars = set(var for var in undefined if var in imports_dict)
        direct_imports = sorted([f"import {var}" for var in imported_vars if not imports_dict[var]])
        imports = sorted([f"from {imports_dict[var]} import {var} " for var in imported_vars if imports_dict[var]])
        
        # Remove imported variables from the undefined set
        undefined = undefined - imported_vars
        
        # Create updated summary tuple
        updated_summary = (defined, undefined, defined_elsewhere)
        
        code = "\n".join(direct_imports) + "\n\n" + "\n".join(imports) + "\n\n" + code
        code = remove_extra_blank_lines_oneline(code.strip())
        analysis_messages = format_analysis_summary(updated_summary)
    else:
        analysis_messages = []
    
    return GeneratedCode(button_type.upper(), dsl, architecture_id, simulation, code, analysis_messages)
    # return GeneratedCode(button_type.upper(), dsl, architecture_id, simulation, code, analysis_messages) + \
    #     Script(f"""
    #     console.log('Button type:', '{button_type}');
    #     if ('{button_type}' in ['STATE', 'NODES', 'CONDITIONS', 'TOOLS', 'DATA', 'LLMS']) {{
    #         console.log('{button_type} tab accessed');
    #         if (typeof initializeCodeMirror === 'function') {{
    #             console.log('Calling initializeCodeMirror for {button_type}');
    #             initializeCodeMirror('{button_type.lower()}');
    #         }} else {{
    #             console.error('initializeCodeMirror function not found');
    #         }}
    #     }}
    #     """)


@rt("/architecture/{arch_id}")
def get(arch_id: int, request: Request):
    arch = architectures.get(arch_id)
    if arch is None:
        raise HTTPException(status_code=404, detail="Architecture not found")
    
    # Check if it's an HTMX request
    if "HX-Request" in request.headers:
        # This is a partial update request
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
                document.getElementById('architecture_id').value = '{arch_id}';
                var dslElement = document.getElementById('dsl');
                if (dslElement) {{
                    dslElement.value = `{arch['graph_spec'].strip()}`;
                    if (window.editor) {{
                        window.editor.setValue(dslElement.value);
                        window.editor.refresh();
                    }}
                }}
                htmx.ajax('POST', '/get_code/README', {{
                    target: '#code-generation-ui',
                    swap: 'outerHTML',
                    values: {{
                        'dsl': dslElement.value,
                        'architecture_id': '{arch_id}',
                        'simulation_code': document.getElementById('simulation_code_checkbox').checked ? 'on' : 'off'
                    }}
                }});
            """)
        )
    else:
        # This is a full page request
        return Main(
            Title(f"LangGraph Architectures - {arch['name']}"),
            TitleHeader(),
            Div(
                TheWholeEnchilada(arch_id),
                id="main_content"
            ),
            Script(f"document.getElementById('current-architecture').textContent = '{arch['name']}';"),
            cls='full-width',
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
    for field in ['state', 'nodes', 'conditions', 'tools', 'data', 'llms']:
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
