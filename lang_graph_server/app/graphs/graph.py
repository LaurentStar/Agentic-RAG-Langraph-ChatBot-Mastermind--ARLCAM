from dotenv import load_dotenv; load_dotenv()
from langgraph.graph import END, StateGraph

# from chains.answer_grader import answer_grader
# from chains.hallucination_grader import hallucination_grader
# from chains.router import RouteQuery, question_router
# from lang_graph_server.app.constants import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH


# ---------------------- Graph State Models ---------------------- #
from app.models.graph_state_models.states import AgentJBallGraphState


from app.nodes.initialization import initialization_nodes



# def decide_to_generate(state):
#     print("---ASSESS GRADED DOCUMENTS---")

#     if state["web_search"]:
#         print(
#             "---DECISION: NOT ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, INCLUDE WEB SEARCH---"
#         )
#         return WEBSEARCH
#     else:
#         print("---DECISION: GENERATE---")
#         return GENERATE


# def grade_generation_grounded_in_documents_and_question(state: GraphState) -> str:
#     print("---CHECK HALLUCINATIONS---")
#     question = state["question"]
#     documents = state["documents"]
#     generation = state["generation"]

#     score = hallucination_grader.invoke(
#         {"documents": documents, "generation": generation}
#     )

#     if hallucination_grade := score.binary_score:
#         print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
#         print("---GRADE GENERATION vs QUESTION---")
#         score = answer_grader.invoke({"question": question, "generation": generation})
#         if answer_grade := score.binary_score:
#             print("---DECISION: GENERATION ADDRESSES QUESTION---")
#             return "useful"
#         else:
#             print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
#             return "not useful"
#     else:
#         print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
#         return "not supported"


# def route_question(state: GraphState) -> str:
#     print("---ROUTE QUESTION---")
#     question = state["question"]
#     source: RouteQuery = question_router.invoke({"question": question})
#     if source.datasource == WEBSEARCH:
#         print("---ROUTE QUESTION TO WEB SEARCH---")
#         return WEBSEARCH
#     elif source.datasource == "vectorstore":
#         print("---ROUTE QUESTION TO RAG---")
#         return RETRIEVE


# workflow = StateGraph(AgentJBallGraphState)

# workflow.add_node(RETRIEVE, retrieve)
# workflow.add_node(GRADE_DOCUMENTS, grade_documents)
# workflow.add_node(GENERATE, generate)
# workflow.add_node(WEBSEARCH, web_search)

# workflow.set_conditional_entry_point(
#     route_question,
#     {
#         WEBSEARCH: WEBSEARCH,
#         RETRIEVE: RETRIEVE,
#     },
# )
# workflow.add_edge(RETRIEVE, GRADE_DOCUMENTS)
# workflow.add_conditional_edges(
#     GRADE_DOCUMENTS,
#     decide_to_generate,
#     {
#         WEBSEARCH: WEBSEARCH,
#         GENERATE: GENERATE,
#     },
# )

# workflow.add_conditional_edges(
#     GENERATE,
#     grade_generation_grounded_in_documents_and_question,
#     {
#         "not supported": GENERATE,
#         "useful": END,
#         "not useful": WEBSEARCH,
#     },
# )
# workflow.add_edge(WEBSEARCH, GENERATE)
# workflow.add_edge(GENERATE, END)

# app = workflow.compile()

class LangGraphApp():
    
    def init_app(self):
        # ---------------------- Import all nodes ---------------------- #
        from app.nodes.bot_actions.bot_action_nodes import extract_message_meta_details_node, decide_how_to_response_node

        # ---------------------- Import all routers ---------------------- #
        from app.nodes.bot_actions.bot_action_nodes import decide_to_respond_route

        self.__class__.jball_agent_app = LangGraphApp.create_jball_workflow(
            extract_message_meta_details_node=extract_message_meta_details_node, 
            decide_how_to_response_node=decide_how_to_response_node,
            decide_to_respond_route=decide_to_respond_route)
        
    @staticmethod
    def create_jball_workflow(**nodes_routes):
        workflow = StateGraph(AgentJBallGraphState)
        workflow.add_node('initialize_jball_state_graph_node', initialization_nodes.initialize_jball_state_graph_node)
        workflow.add_node('extract_message_meta_details_node', nodes_routes['extract_message_meta_details_node'])
        workflow.add_node('decide_how_to_response_node', nodes_routes['decide_how_to_response_node'])
        
        workflow.add_conditional_edges('extract_message_meta_details_node', nodes_routes['decide_to_respond_route'],
            {
                True: 'decide_how_to_response_node',
                False: END,
            },
        )

        workflow.add_edge('initialize_jball_state_graph_node', 'extract_message_meta_details_node')
        workflow.add_edge('decide_how_to_response_node', END)
        workflow.set_entry_point("initialize_jball_state_graph_node")
        
        return workflow.compile()
    
    jball_agent_app = None
