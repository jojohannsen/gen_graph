from fasthtml.common import *
from gen_graph import gen_graph
import uuid

def before(session):
  if not 'sid' in session: session['sid'] = str(uuid.uuid4())


app,rt = fast_app(hdrs=[picolink, MarkdownJS(), HighlightJS()])

BLANK_EXAMPLE = "examples..."
examples = { BLANK_EXAMPLE: "",
"Agent Executor": """
START(State) => call_model

call_model
  should_call_tool => tool_node

tool_node => call_model

""",
"Tool Selector": """
START(State) => select_tools

select_tools => agent

agent
  should_call_tool => tool_node
  => END

tool_node => agent

""",
"Branching 1": """
START(State)  => a

a => b, c

b => b2

b2, c => d

d => END
""", 
"Branching 2": """
aaa(State)
   bc => bbb, ccc
   cd => ccc, ddd

bbb => eee
ccc => eee
ddd => eee
eee => END

""",
"Branching 3": """
START(State) => a

a
  to_cd => c, d
  => b, c

b, c => e
c, d => e

e => END
"""}

    
@rt("/convert")
def post(dsl:str, example:str, lastval:str): 
    #print(dsl)
    if dsl:
        print(f"DSL has content: {dsl[:50]}")
    else:
        print("DSL is blank")
    print(example)
    print(lastval)
    return Pre(Code(gen_graph("graph", dsl))) if dsl else '', create_textarea(example, dsl)

def create_textarea(selection, dsl):
    print(f"create_textarea: {selection}")
    if selection != BLANK_EXAMPLE:
        dsl = examples[selection]
    return Textarea(dsl,placeholder='DSL text goes here', id="dsl", rows=10, hx_swap_oob='true'), Hidden(id="lastval", value=selection)

instructions = {
    "First line must contain the State class and the first node":  ["START(StateClassName) => first_node"],
    "Nodes start on left margin": ["first_node => second_node"],
    "Conditions MUST be indented, and show the name of the conditional function": ["node_1", "  should_call_tool => tool_node", "  conditionY => node_3"],
    "The conditional function looks like this:": ["def should_call_tool(state: State) -> bool:", "  # your code here", "  return state['some_key'] == 'call_a_tool'"],
}

@rt("/")
def get():
    return Div(Div(
        Div(
            Form(hx_post='/convert', 
                target_id="lg_gen", 
                hx_trigger="change from:#example")(
                Div(H6('LangGraph DSL', cls='col'),
                Select(style="width: auto", id="example", cls='col')(
                    Option(BLANK_EXAMPLE, selected=True), 
                    Option("Agent Executor"),
                    Option("Tool Selector"),
                    Option("Branching 1"),
                    Option("Branching 2"),
                    Option("Branching 3"),
                ), Button('Generate Code', hx_post='/convert', target_id="lg_gen", style="display: inline-flex; align-items: center; justify-content: center; height:50px;"), cls='grid'),
                create_textarea(BLANK_EXAMPLE, "")),
            Div(Ol(Li(Div(s), Pre("\n".join([line for line in code]))) for s,code in instructions.items())),
            cls='col'
        ),
        Div(
            Div(
                Div(H6('Python Code'), cls='col'),
                Div(
                    A('View README', hx_get='/about', target_id="about_lg_gen"), 
                    cls='col'
                ), 
                cls='grid'
            ),
            Pre(id="lg_gen"),
            Div(id="about_lg_gen"),
            cls='col'
        ),
        cls='grid', style='margin: 50px'
    ), cls='page-container')

 
with open('README.md') as f: 
    about_md = f.read()

@rt("/about")
def get():
  return Div(about_md, cls='marked', style='text-align: left;')

serve()

