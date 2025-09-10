from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from chains.answer_grader import answer_grader
from chains.hallucination_grader import hallucination_grader
from chains.router import RouteQuery, question_router
from lang_graph_server.app.constants import BotActions
from nodes.bot_actions import bot_action_nodes
from app.graphs.states import AgentJBallGraphState

load_dotenv()

#--------------------------------------#
# The Graph State of the Agent J- Ball #
#--------------------------------------#
workflow = StateGraph(AgentJBallGraphState)

# workflow.add_node(BotActions.DECIDE_TO_RESPONSE, bot_action_nodes.)
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

# lang_graph_app = workflow.compile()


