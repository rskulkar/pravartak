# smoke_test.py

# ##
# ## INTAKE AGENT SMOKE TEST
# ## 
# import json 
# from anthropic import Anthropic
# from prompts import INTAKE_AGENT_PROMPT
# 
# client = Anthropic()
# 
# print("=" * 60)
# print("INTAKE AGENT SMOKE TEST")
# print("=" * 60)
# 
# response = client.messages.create(
#     model = "claude-sonnet-4-5",
#     max_tokens = 1024,
#     system = INTAKE_AGENT_PROMPT,
#     messages = [
#         {
#             "role": "user",
#             "content": (
#                 "I'm looking for a 2BHK apartment in Whitefield, Bengaluru. "
#                 "My budget is between ₹60L and ₹80L. I need possession within "
#                 "12 months. Must have a gym. I work in the IT corridor and "
#                 "prefer to be close to the metro."
#             )
#         }
#     ]   
# )
# 
# print(response.content[0].text)

##
## TESTING THE INVENTORY SEARCH IN ISOLATION
## 
# from graph import build_graph, search_node, intake_node
# from state import GraphState, BuyerProfile
# from inventory import search_properties
# 
# print("=" * 60)
# print("DIAGNOSTIC SMOKE TEST — DIRECORY INVERNTORY CHECK")
# print("=" * 60)
# 
# # Scenario A — clean run, no recovery expected
# print("\nSCENARIO A — First-time buyer, Whitefield, ₹80L, 2BHK")
# print("-" * 60)
# 
# profile_a = BuyerProfile(
#     budget_min_lakhs=60,
#     budget_max_lakhs=80,
#     locations=["Whitefield"],
#     property_type="apartment",
#     bhk=2,
#     possession_months=12,
#     must_haves=["gym"],
#     lifestyle_tags=["it_corridor", "metro_nearby"],
# )
# 
# results_a = search_properties(profile_a)
# print(f"Found {len(results_a)} properties matching criteria for Scenario A:")
# for prop in results_a:
#     print(f" {prop.property_id} | {prop.title} | {prop.price_lakhs}L")
# 
# profile_b = BuyerProfile(
#     budget_min_lakhs=96,
#     budget_max_lakhs=120,
#     locations=["Sarjapur Road"],
#     property_type="villa",
#     bhk=3,
#     possession_months=12,
# )
# results_b = search_properties(profile_b)
# print(f"\nFound {len(results_b)} properties matching criteria for Scenario B:")
# for prop in results_b:
#     print(f" {prop.property_id} | {prop.title} | {prop.price_lakhs}L")

##
## TESTING THE FULL GRAPH INTEGRATION
## 
from graph import run
# Scenario A — clean run, no recovery expected
print("=" * 60)
print("SCENARIO A — First-time buyer, Whitefield, ₹80L, 2BHK")
print("=" * 60)

report_a = run(
    "I'm looking for a 2BHK apartment in Whitefield, Bengaluru. "
    "My budget is between ₹60L and ₹80L. I need possession within "
    "12 months. Must have a gym. I work in the IT corridor and "
    "prefer to be close to the metro."
)
print(report_a)

print("\n" + "=" * 60)
print("SCENARIO B — Retiree couple, Sarjapur Road, ₹1.2Cr, villa")
print("=" * 60)

report_b = run(
    "My wife and I are retiring and looking for a 3BHK villa on "
    "Sarjapur Road, Bengaluru. Budget is ₹1.2 crore. We need an "
    "elevator in the building and a gated community with good "
    "security. School nearby is a plus for our grandchildren. "
    "Possession within 12 months preferred."
)
print(report_b)