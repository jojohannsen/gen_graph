from fasthtml.common import *
from fastlite import database
from langgraph_codegen import gen_graph, gen_nodes, gen_conditions, gen_state
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

BUTTON_TYPES = ['README', 'STATE', 'NODES', 'CONDITIONS', 'GRAPH', 'REASONING']

def filename_to_url(name: str) -> str:
    name = name.lower().replace(' ', '-').replace(',', '').replace('(', '').replace(')', '')
    return re.sub(r'[^a-z0-9-]', '', name)

def get_grouped_architectures(architectures: dict) -> dict:
    # First pass: collect all categories and their order
    category_info = {}
    for arch in architectures.values():
        raw_category = arch.get('category', 'Uncategorized')
        parts = raw_category.split('_', 1)
        
        if len(parts) == 2 and parts[0].isdigit():
            order = int(parts[0])
            category = parts[1]
        else:
            order = float('inf')  # Unordered categories go last
            category = raw_category
            
        if category not in category_info:
            category_info[category] = {
                'order': order,
                'architectures': []
            }
        category_info[category]['architectures'].append(arch)
    
    # Sort categories by order and create final ordered dictionary
    sorted_categories = sorted(
        category_info.items(),
        key=lambda x: (x[1]['order'], x[0].lower())  # Sort by order first, then alphabetically
    )
    
    # Create the final ordered dictionary
    grouped_architectures = {}
    for category, info in sorted_categories:
        grouped_architectures[category] = info['architectures']
    
    return grouped_architectures

def GraphArchitecture(selected_example: str = None):
    if selected_example is None:
        selected_example = next(iter(architectures.keys()))

    grouped_architectures = get_grouped_architectures(architectures)

    return Div(
        # Hidden field "architecture_id" identies the currently displayed architecture
        Hidden(selected_example, id="architecture_id", name="architecture_id", hx_swap="outerHTML"),
        Div(
            *[Details(
                Summary(category, role="contentinfo", cls="category-summary outline secondary"),
                Div(
                    *[Div(
                        A(arch['name'],
                          id=f"example-link-{filename_to_url(arch['name'])}",
                          cls=f"example-link{' selected' if arch['id'] == selected_example else ''}",
                          hx_get=f"/architecture/{arch['id']}",
                          hx_target="#dsl",
                          hx_trigger="click, keyup[key=='Enter']",
                          hx_on="htmx:afterOnLoad: function() { if (typeof update_editor !== 'undefined') { setTimeout(update_editor, 100); } }",
                        ),
                    ) for arch in architectures],
                    cls="category-content",
                ),
                cls="architecture-category",
                open="open"  # Makes the section expanded by default
            ) for category, architectures in grouped_architectures.items()],
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
    elif button_type == 'REASONING':
        # Return a message about selecting a specific reasoning component
        return "# Select a specific reasoning component (Tools, Data, or LLMs) to view its implementation"
    elif simulation:
        simulation_functions = {
            'STATE': gen_state,
            'NODES': gen_nodes,
            'CONDITIONS': gen_conditions,
            'TOOLS': lambda _: arch['tools'].strip(),
            'DATA': lambda _: arch['data'].strip(),
            'LLMS': lambda _: "# LLMs simulation not implemented"
        }
        return simulation_functions[button_type](arch['graph_spec']).strip()
    else:
        value = arch.get(button_type.lower(), '')
        if value is not None:
            return value.strip()
        else:
            return ""


def CodeGenerationButtons(active_button: str, architecture_id: str, simulation: bool):
    button_labels = {
        'README': 'README',
        'STATE': 'State',
        'NODES': 'Nodes',
        'CONDITIONS': 'Conditions',
        'GRAPH': 'Graph',
        'REASONING': 'Reasoning',
        'TOOLS': 'Tools',
        'DATA': 'Structured Output',
        'LLMS': 'LLMs'
    }
    
    # Create main buttons with special case for REASONING
    main_buttons = [Button(button_labels[btn], id=f"{btn.lower()}_button", 
                          hx_post=f'/get_code/{btn}', 
                          target_id='code-generation-ui', 
                          hx_swap='outerHTML',
                          hx_trigger="click",
                          hx_include="#dsl",
                          # Add active class if this button is active OR if it's the Reasoning button and a child is active
                          cls=f'code-generation-button{" active" if active_button == btn or (btn == "REASONING" and active_button in ["TOOLS", "DATA", "LLMS"]) else ""}')
                   for btn in BUTTON_TYPES]
    
    # Create sub-buttons for Reasoning with new order
    sub_buttons = []
    if active_button == 'REASONING' or active_button in ['TOOLS', 'DATA', 'LLMS']:
        sub_buttons = [
            Button(button_labels[btn], id=f"{btn.lower()}_button", 
                   hx_post=f'/get_code/{btn}', 
                   target_id='code-generation-ui', 
                   hx_swap='outerHTML',
                   hx_trigger="click",
                   hx_include="#dsl",
                   cls=f'code-generation-button sub-button{" active" if active_button == btn else ""}')
            for btn in ['LLMS', 'DATA', 'TOOLS']
        ]
    
    return Div(  
        Div(*main_buttons, cls='main-buttons'),
        Div(*sub_buttons, cls='sub-buttons') if sub_buttons else "",
        Span(style="flex-grow: 1;"),
        # Hidden simulation checkbox
        Label(
            Input(type="checkbox", name="simulation_code", id="simulation_code_checkbox",
                  hx_post=f'/get_code/{active_button}',
                  hx_target='#code-generation-ui',
                  hx_swap='outerHTML',
                  hx_include='#dsl,#architecture_id',
                  hx_trigger="change, refreshContent from:#code-generation-ui",
                  checked=simulation,
                  disabled=active_button == 'GRAPH',
                  style="display: none;"),  # Hide the checkbox
            Span("Simulation Code", 
                 style="display: none;"),  # Hide the label text
            style="display: none;"  # Hide the entire label container
        ),
        id='code-generation-buttons',
        cls='toggle-buttons',
        style="display: flex; flex-direction: column; gap: 10px;"
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

def make_form(example_id: str):
    initial_dsl = architectures[int(example_id)]['graph_spec']
    
    # Analyze the initial architecture
    analyzer = analyze_architecture_code(int(example_id))
    readme_summary = analyzer.get_snippet_summary('readme') or (set(), set(), set())
    analysis_messages = format_analysis_summary(readme_summary)
    
    return Form()(
        Div(
            Div(GraphArchitecture(example_id), cls='left-column'),
            Div(
                Div(
                    Textarea(initial_dsl, placeholder='DSL text goes here', id="dsl", name="dsl", rows=25, cls="code-editor"),
                    cls='middle-column'
                ),
                GeneratedCode('README', initial_dsl, example_id, False, 
                             architectures[int(example_id)]['readme'], 
                             analysis_messages),
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
            Textarea(content, 
                     id=f"{active_button.lower()}-code-editor", 
                     name=f"{active_button.lower()}-code-editor", 
                     cls="code-editor",  
                     data_language="python"),
            cls=f'tab-content active'
        )
    else:
        return Div(Pre(Code(content, cls='language-python'), id=f"{active_button.lower()}-code"),
                   cls=f'tab-content active')

@rt("/get_code/{button_type}")
def post(button_type: str, dsl: str, architecture_id: str, simulation_code: str = "false"):
    simulation = simulation_code == "on" and button_type != 'GRAPH'
    skip_imports = button_type == 'GRAPH'
    
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
        direct_imports = sorted([f"import {var}" for var in undefined if not imports_dict.get(var, False)])
        imports = sorted([f"from {imports_dict[var]} import {var} " for var in undefined if imports_dict.get(var, False)])
        
        # Remove imported variables from the undefined set
        undefined = undefined - imported_vars
        
        # Create updated summary tuple
        updated_summary = (defined, undefined, defined_elsewhere)
        
        if not skip_imports:
            code = "\n".join(direct_imports) + "\n\n" + "\n".join(imports) + "\n\n" + code
        code = remove_extra_blank_lines_oneline(code.strip())
        analysis_messages = format_analysis_summary(updated_summary)
    else:
        analysis_messages = []
    
    return GeneratedCode(button_type.upper(), dsl, architecture_id, simulation, code, analysis_messages)


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
            GraphArchitecture(arch_id),
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
        ), HtmxResponseHeaders(push_url=f"/graph/{filename_to_url(arch['name'])}")
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


def analyze_architecture_code(architecture_id: int) -> CodeSnippetAnalyzer:
    arch = architectures[architecture_id]
    
    if arch is None:
        raise ValueError(f"Architecture with id {architecture_id} not found")

    analyzer = CodeSnippetAnalyzer()

    # Analyze each code snippet
    for field in ['state', 'nodes', 'conditions', 'tools', 'data', 'llms']:
        fv = arch.get(field, '')
        if fv is not None:
            code = fv.strip()
            if code:
                analyzer.add_snippet(field, code)

    # Generate and analyze graph code
    graph_code = gen_graph(mk_name(arch['name']), arch['graph_spec']).strip()
    analyzer.add_snippet('graph', graph_code)

    # Perform analysis on all snippets
    analyzer.analyze_all_snippets()

    return analyzer

@rt("/graph/{architecture_name}")
def get(architecture_name: str, request: Request):
    # Find the architecture by name
    arch = next((a for a in architectures.values() if filename_to_url(a['name']) == architecture_name), None)
    if arch is None:
        raise HTTPException(status_code=404, detail="Architecture not found")
    
    arch_id = arch['id']
    
    # Check if it's an HTMX request
    if "HX-Request" in request.headers:
        # This is a partial update request
        return (
            arch['graph_spec'].strip(), 
            GraphArchitecture(arch_id),
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
        ), HtmxResponseHeaders(push_url=f"/graph/{architecture_name}")

serve()
