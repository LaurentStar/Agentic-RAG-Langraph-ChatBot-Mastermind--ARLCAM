from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

# from chains.answer_grader import answer_grader
# from chains.hallucination_grader import hallucination_grader
# from chains.router import RouteQuery, question_router
# from lang_graph_server.app.constants import GENERATE, GRADE_DOCUMENTS, RETRIEVE, WEBSEARCH



# ---------------------- Nodes ---------------------- #
# from nodes import generate, grade_documents, retrieve, web_search



from app.graphs.states import AgentJBallGraphState

load_dotenv()


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
        # ---------------------- Delayed importing of Nodes ---------------------- #
        from app.graphs.nodes.bot_actions.bot_action_nodes import extract_tone_node        
        self.__class__.jball_agent_app = LangGraphApp.create_jball_workflow(extract_tone_node)
        
    @staticmethod
    def create_jball_workflow(extract_tone_node):
        workflow = StateGraph(AgentJBallGraphState)
        workflow.add_node('get_tone', extract_tone_node)
        workflow.set_entry_point("get_tone")

        return workflow.compile()
    
    jball_agent_app = None
