import pytest
from gen_graph_x import gen_graph_x, Graph

def test_graph_equivalence():
    # Test case 1: Simple equivalent graphs
    graph1 = Graph()
    graph1.set_start_node("A")
    graph1.set_end_node("B")
    graph1.add_edge("A", "B", "true")

    graph2 = Graph()
    graph2.set_start_node("X")
    graph2.set_end_node("Y")
    graph2.add_edge("X", "Y", "true")

    assert graph1.is_structurally_equivalent(graph2)

    # Test case 2: Complex equivalent graphs
    graph3 = Graph()
    graph3.set_start_node("Start")
    graph3.set_end_node("End")
    graph3.add_edge("Start", "Middle1", "condition1")
    graph3.add_edge("Start", "Middle2", "condition2")
    graph3.add_edge("Middle1", "End", "true")
    graph3.add_edge("Middle2", "End", "true")

    graph4 = Graph()
    graph4.set_start_node("Begin")
    graph4.set_end_node("Finish")
    graph4.add_edge("Begin", "Intermediate1", "cond_a")
    graph4.add_edge("Begin", "Intermediate2", "cond_b")
    graph4.add_edge("Intermediate1", "Finish", "true")
    graph4.add_edge("Intermediate2", "Finish", "true")

    assert graph3.is_structurally_equivalent(graph4)

    # Test case 3: Non-equivalent graphs (different condition types)
    graph5 = Graph()
    graph5.set_start_node("S")
    graph5.set_end_node("E")
    graph5.add_edge("S", "M", "condition")
    graph5.add_edge("M", "E", "true")

    graph6 = Graph()
    graph6.set_start_node("S")
    graph6.set_end_node("E")
    graph6.add_edge("S", "M", "true")
    graph6.add_edge("M", "E", "condition")

    assert not graph5.is_structurally_equivalent(graph6)

    # Test case 4: Non-equivalent graphs (different structure)
    graph7 = Graph()
    graph7.set_start_node("S")
    graph7.set_end_node("E")
    graph7.add_edge("S", "M", "condition")
    graph7.add_edge("M", "E", "true")

    graph8 = Graph()
    graph8.set_start_node("S")
    graph8.set_end_node("E")
    graph8.add_edge("S", "E", "condition")

    assert not graph7.is_structurally_equivalent(graph8)

def test_gen_graph_x():
    graph_spec = """
START(State) => Node1
Node1 => Node2
Node2 => END
    """
    graph_output, graph_object = gen_graph_x("test_graph", graph_spec)
    
    assert isinstance(graph_output, str)
    assert isinstance(graph_object, Graph)
    assert graph_object.start_node == "Node1"
    assert "Node2" in graph_object.nodes
    assert ("Node2", "true") in graph_object.edges["Node1"]

def test_compare_graphs():
    graph1 = """
START(State) => Node1
Node1 => Node2
Node2 => END
    """
    graph2 = """
START(XGState) => HoHo
HoHo => HaHa
HaHa => END
    """
    graph3 = """
START(XGState) => HoHo
HoHo => HaHa
HaHa => ExtraNode
ExtraNode => END
    """
    _, graph1_object = gen_graph_x("test_graph", graph1)
    _, graph2_object = gen_graph_x("test_graph", graph2)
    _, graph3_object = gen_graph_x("test_graph", graph3)
    assert graph1_object.is_structurally_equivalent(graph2_object)
    assert not graph1_object.is_structurally_equivalent(graph3_object)


def test_compare_graphs_conditional_edges():
    graph1 = """
START(State) => Node1

Node1
  conditionA => Node2

Node2
  conditionB => END
  => Node1
    """
    graph2 = """
START(State) => Node1

Node1
  is_ready_to_move_one => Node2

Node2
  conditionB => END
  => Node1
    """
    graph3 = """
START(State) => Node1

Node1
  conditionA => Node2

Node2
  conditionB => END
  => Node1
    """
    _, graph1_object = gen_graph_x("test_graph", graph1)
    _, graph2_object = gen_graph_x("test_graph", graph2)
    _, graph3_object = gen_graph_x("test_graph", graph3)
    assert graph1_object.is_structurally_equivalent(graph2_object)
    assert not graph1_object.is_structurally_equivalent(graph3_object)

