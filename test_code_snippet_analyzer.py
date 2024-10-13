import pytest
from code_utils.code_snippet_analyzer import CodeSnippetAnalyzer

@pytest.fixture
def analyzer():
    return CodeSnippetAnalyzer()

class TestAnalyzeCode:
    def test_simple_assignment(self, analyzer):
        code = "x = 5"
        assert analyzer.analyze_code(code) == ({'x'}, set())

    def test_multiple_assignments(self, analyzer):
        code = "x = y = z = 10"
        assert analyzer.analyze_code(code) == ({'x', 'y', 'z'}, set())

    def test_variable_usage(self, analyzer):
        code = "x = 5\ny = x + 10"
        assert analyzer.analyze_code(code) == ({'x', 'y'},{'x'})

    def test_undefined_variable(self, analyzer):
        code = "y = x + 10"
        assert analyzer.analyze_code(code) == ({'y'}, {'x'})

    def test_function_definition(self, analyzer):
        code = """
def foo(a, b):
    return a + b
x = foo(1, 2)
"""
        assert analyzer.analyze_code(code) == ({'a', 'b', 'foo', 'x'}, {'foo', 'a', 'b'})

    def test_function_with_undefined_variable(self, analyzer):
        code = """
def foo(a):
    return a + b
x = foo(1)
"""
        assert analyzer.analyze_code(code) == ({'a', 'foo', 'x'}, {'foo', 'a', 'b'})

    def test_complex_scenario(self, analyzer):
        code = """
x = 10
def foo(a):
    y = x + a
    return y + z
result = foo(5)
"""
        assert analyzer.analyze_code(code) == ({'a', 'foo', 'result', 'x', 'y'}, {'y', 'z', 'x', 'a', 'foo'})

    def test_import_statement(self, analyzer):
        code = "import math\nx = math.pi"
        assert analyzer.analyze_code(code) == ({'math', 'x'}, {'math'})

    def test_class_definition(self, analyzer):
        code = """
class MyClass:
    def __init__(self, x):
        self.x = x
    
    def method(self):
        return self.x + y

obj = MyClass(10)
"""
        assert analyzer.analyze_code(code) == ({'MyClass', '__init__', 'method', 'obj', 'self', 'x'}, {'x', 'self', 'MyClass', 'y'})

    def test_list_comprehension(self, analyzer):
        code = "[x for x in range(10) if x > y]"
        assert analyzer.analyze_code(code) == ({'x'}, {'x', 'range', 'y'})

    def test_invalid_syntax(self, analyzer):
        code = "x = "
        assert analyzer.analyze_code(code) == (set(), set())

big_snippet = '''
async def execute_step(state: PlanExecute):
    plan = state["plan"]
    plan_str = "\\n".join(f"{i+1}. {step}" for i, step in enumerate(plan))
    task = plan[0]

    agent_response = await agent_executor.ainvoke(
        {"messages": [("user", task_formatted)]}
    )
    return {
        "past_steps": (task, agent_response["messages"][-1].content),
    }

async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({"messages": [("user", state["input"])]})
    return {"plan": plan.steps}

async def replan_step(state: PlanExecute):
    output = await replanner.ainvoke(state)
    if isinstance(output.action, Response):
        return {"response": output.action.response}
    else:
        return {"plan": output.action.steps}'''

class TestSnippetManagement:
    def test_big_snippet(self, analyzer):
        result = analyzer.analyze_code(big_snippet)
        pass # just testing that it runs
        #assert analyzer.analyze_code(big_snippet) == ({'tools', 'tool_node', 'tavily_tool', 'python_repl', 'llm', 'chart_agent', 'chart_node', 'research_agent', 'research_node', 'create_agent', 'agent_node', 'tool_names', 'system_message', 'prompt', 'x', 'y', 'z', 'result', 'obj', 'MyClass', 'method', 'x'}, {'y', 'z', 'x', 'a', 'foo'})

    def test_add_snippet(self, analyzer):
        analyzer.add_snippet('snippet1', 'x = 5')
        assert 'snippet1' in analyzer.snippets
        assert analyzer.snippets['snippet1']['defined'] == {'x'}
        assert analyzer.snippets['snippet1']['used'] == set()


    def test_analyze_all_snippets(self, analyzer):
        analyzer.add_snippet('snippet1', 'x = 5\ny = x + z')
        analyzer.add_snippet('snippet2', 'z = 10\nprint(x)')
        analyzer.analyze_all_snippets()

        assert analyzer.get_snippet_summary('snippet1') == ({'x', 'y'}, set(), {'z'})
        assert analyzer.get_snippet_summary('snippet2') == ({'z'}, set(), {'x', 'print'})

    def test_get_all_summaries(self, analyzer):
        analyzer.add_snippet('snippet1', 'x = 5\ny = x + z')
        analyzer.add_snippet('snippet2', 'z = 10\nprint(x)')
        analyzer.analyze_all_snippets()

        summaries = analyzer.get_all_summaries()
        assert 'snippet1' in summaries
        assert 'snippet2' in summaries
        assert summaries['snippet1'] == ({'x', 'y'}, set(), {'z'})
        assert summaries['snippet2'] == ({'z'}, set(), {'x', 'print'})

    def test_nonexistent_snippet(self, analyzer):
        assert analyzer.get_snippet_summary('nonexistent') is None


if __name__ == "__main__":
    pytest.main()
