import pytest
from code_utils.code_snippet_analyzer import CodeSnippetAnalyzer

@pytest.fixture
def analyzer():
    return CodeSnippetAnalyzer()

def test_simple_assignment(analyzer):
    code = "x = 5"
    assert analyzer.analyze_code(code) == ({'x'}, set())

def test_multiple_assignments(analyzer):
    code = "x = y = z = 10"
    assert analyzer.analyze_code(code) == ({'x', 'y', 'z'}, set())

def test_variable_usage(analyzer):
    code = "x = 5\ny = x + 10"
    assert analyzer.analyze_code(code) == ({'x', 'y'}, {'x'})

def test_undefined_variable(analyzer):
    code = "y = x + 10"
    assert analyzer.analyze_code(code) == ({'y'}, {'x'})

def test_function_definition(analyzer):
    code = """
def foo(a, b):
    return a + b
x = foo(1, 2)
"""
    assert analyzer.analyze_code(code) == ({'a', 'b', 'foo', 'x'}, {'foo', 'a', 'b'})

def test_function_with_undefined_variable(analyzer):
    code = """
def foo(a):
    return a + b
x = foo(1)
"""
    assert analyzer.analyze_code(code) == ({'a', 'foo', 'x'}, {'a', 'b', 'foo'})

def test_complex_scenario(analyzer):
    code = """
x = 10
def foo(a):
    y = x + a
    return y + z
result = foo(5)
"""
    result = analyzer.analyze_code(code)
    assert analyzer.analyze_code(code) == ({'result', 'foo', 'x', 'y', 'a'}, {'foo', 'x', 'y', 'z', 'a'})

def test_import_statement(analyzer):
    code = "import math\nx = math.pi"
    assert analyzer.analyze_code(code) == ({'math', 'x'}, {'math'})

def test_class_definition(analyzer):
    code = """
class MyClass:
    def __init__(self, x):
        self.x = x
    
    def method(self):
        return self.x + y

obj = MyClass(10)
"""
    assert analyzer.analyze_code(code) == ({'MyClass', '__init__', 'method', 'obj', 'self', 'x'}, 
                                           {'self', 'MyClass', 'x', 'y'})

def test_list_comprehension(analyzer):
    code = "[x for x in range(10) if x > y]"
    assert analyzer.analyze_code(code) == ({'x'}, {'y', 'x', 'range'})

def test_invalid_syntax(analyzer):
    code = "x = "
    assert analyzer.analyze_code(code) == (set(), set())

if __name__ == "__main__":
    pytest.main()
