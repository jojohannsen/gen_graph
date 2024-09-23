
This is a tool for generating langgraph builder code from a DSL.  

It's not that hard to just write the builder code, 
but there's two reasons you might find it useful:

1. You want to see your graph *before* you write the builder code.
2. You want to know what code you need to write for conditional edges.

##### Example

Here's a simple example that shows the syntax:

```
START(State) => agent_node

agent_node
  should_continue => tool_node
  => END

tool_node => agent_node
```

This tells me exactly what code I need to write:

1. START(State) -- this tells me I need a State class for my graph
2. agent_node, tool_node -- these are normal Nodes, 
functions that take state and return state updates
3. should_continue -- this is a boolean function that 
takes state and returns True if I should call tool_node

That's it.  I can just look at the graph and 
know what code I need to write.

##### What does it look like in practice?

Here's a more complicated example -- a graph that takes user input, 
gives it to openai and anthropic, 
let's a human choose which result is better, 
and keeps a count until the user quits.

```python
graph_spec = """

START(ModelCompare) => call_model

call_model => call_openai_model, call_anthropic_model

call_openai_model, call_anthropic_model => human_chooses

human_chooses => handle_human_request

handle_human_request
  wants_to_quit => END
  => call_model

"""

# make compiled graph in variable model_compare
graph_code = gen_graph("model_compare", graph_spec)
exec(graph_code)

model_compare.invoke({"human_request": "tell me a joke about turtles"})
```

This plus the 5 node functions, and the 1 conditional edge function, is the entire program.  

The generated code (below) is not that complicated, but I can't see the graph and I can't make sense of what 'add_conditional_edges' is doing.

```python
model_compare = StateGraph(ModelCompare)
model_compare.add_node('call_model', call_model)
model_compare.add_node('call_openai_model', call_openai_model)
model_compare.add_node('call_anthropic_model', call_anthropic_model)
model_compare.add_node('human_chooses', human_chooses)
model_compare.add_node('handle_human_request', handle_human_request)
model_compare.add_edge(START, 'call_model')
model_compare.add_edge('call_model', 'call_openai_model')
model_compare.add_edge('call_model', 'call_anthropic_model')
model_compare.add_edge(['call_openai_model','call_anthropic_model'], 'human_chooses')
model_compare.add_edge('human_chooses', 'handle_human_request')
def after_handle_human_request(state: ModelCompare):
    if wants_to_quit(state):
        return 'END'
    return 'call_model'

handle_human_request_dict = {'END': END, 'call_model': 'call_model'}
model_compare.add_conditional_edges('handle_human_request', after_handle_human_request, handle_human_request_dict)


model_compare = model_compare.compile()
```

#### Limitations

- No syntax checking, mistakes show up when executing generated code
- UI doesn't show any errors
- This isn't a product, it's something I've been experimenting with, also trying out [FastHTML](https://about.fastht.ml/).