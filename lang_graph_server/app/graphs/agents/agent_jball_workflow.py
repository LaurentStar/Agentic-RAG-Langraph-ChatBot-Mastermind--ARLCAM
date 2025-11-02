from langgraph.graph import END, StateGraph
from app.constants import Node
# from chains.answer_grader import answer_grader
# from chains.hallucination_grader import hallucination_grader
# from chains.router import RouteQuery, question_router
# from lang_graph_server.app.constants import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH


# ---------------------- Graph State Models ---------------------- #
from app.models.graph_state_models.agent_graph_states import AgentGraphStateBase

# ---------------------- Import all nodes ---------------------- #
from app.nodes.bot_actions.bot_action_nodes import extract_message_meta_details_node, decide_how_to_response_node

# ---------------------- Import all routers ---------------------- #
from app.nodes.bot_actions.bot_action_nodes import decide_to_respond_router

from app.nodes.initialization import initialization_nodes



class AgentJBallWorkflow:
    
    def __init__(self):
        #_______ Define and compile the graph _______#
        self.workflow = StateGraph(AgentGraphStateBase)
        self.workflow.add_node(Node.INITIALIZATION, initialization_nodes.initialize_jball_state_graph_node)
        self.workflow.add_node("extract_message_meta_details_node", extract_message_meta_details_node)
        self.workflow.add_node('decide_how_to_response_node', decide_how_to_response_node)
        
        self.workflow.add_conditional_edges('extract_message_meta_details_node', decide_to_respond_router,
            {
                True: 'decide_how_to_response_node',
                False: END,
            },
        )

        # self.workflow.add_edge('initialize_jball_state_graph_node', 'extract_message_meta_details_node')
        # self.workflow.add_edge('decide_how_to_response_node', END)
        self.workflow.add_edge(Node.INITIALIZATION, "extract_message_meta_details_node")
        self.workflow.add_edge("extract_message_meta_details_node", "decide_how_to_response_node")
        self.workflow.add_edge("decide_how_to_response_node", END)

        self.workflow.set_entry_point(Node.INITIALIZATION)
        
        self.app = self.workflow.compile()
    
    def run(self, initial_state:dict, thread_id:str='default') -> dict:
        return self.app.invoke(initial_state, {"configurable" : {"thread_id": thread_id}})
    
    
    def arun(self, initial_state:dict, thread_id:str='default') -> dict:
        return self.app.ainvoke(initial_state, {"configurable" : {"thread_id": thread_id}})
