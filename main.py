from fasthtml.common import *
from gen_graph import gen_graph


app,rt = fast_app(hdrs=[HighlightJS()])
examples = { "0": "",
"1": """
START(State) => call_model

call_model
  should_call_tool => tool_node

tool_node => call_model

""",
"2": """
START(State) => select_tools

select_tools => agent

agent
  should_call_tool => tool_node
  => END

tool_node => agent

""",
"3": """
START(State)  => a

a => b, c

b => b2

b2, c => d

d => END
""", 
"4": """
aaa(State)
   bc => bbb, ccc
   cd => ccc, ddd

bbb => eee
ccc => eee
ddd => eee
eee => END

""",
"5": """
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
    print(dsl)
    print(example)
    print(lastval)
    if example != "0" and lastval != example:
        dsl = examples[example]
    return Pre(Code(gen_graph("graph", dsl))) if dsl else '', create_textarea(example)

def create_textarea(selection):
    dsl = examples[selection]
    return Textarea(dsl,placeholder='DSL text goes here', id="dsl", rows=10, hx_swap_oob='true'), Hidden(id="lastval", value=selection)

@rt("/")
def get():
    return Titled(
        "Generate LangGraph builder code",

        Form(hx_post='/convert', target_id="lg_gen", hx_trigger="change from:#example, keyup delay:500ms from:#dsl")(
            Select(style="width: auto", id="example")(
                Option("blank", value="0", selected=True), 
                Option("Agent Executor", value="1"),
                Option("Tool Selector", value="2"),
                Option("Branching 1", value="3"),
                Option("Branching 2", value="4"),
                Option("Branching 3", value="5"),
),
            create_textarea("0"),
        Div(id="lg_gen")))

serve()

