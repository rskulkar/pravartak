#!/usr/bin/env python
# coding: utf-8

# # INSTALLATION, ETC.

# In[1]:


get_ipython().system('pip install langchain langchain-anthropic anthropic')


# # IMPORTS

# In[2]:


get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')

import warnings
def warn(*args, **kwargs):
    pass
warnings.warn = warn
warnings.filterwarnings('ignore')

import os, subprocess
from IPython.display import Markdown, display


# ## SET UP CLAUDE KEY

# In[3]:


## extract anthropic api key from zsh environment and set it in os.environ for langchain-anthropic to work
key = subprocess.check_output(
    "zsh -lc 'source ~/.zshrc >/dev/null 2>&1; printf %s \"$ANTHROPIC_API_KEY\"'",
    shell=True,
    text=True
).strip()

os.environ["ANTHROPIC_API_KEY"] = key
print(bool(key))


# ### SETUP CONNECTION AND TEST CONNECTION

# In[4]:


from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    temperature=0.2
)

resp = llm.invoke("Say hello in one short sentence.")
display(Markdown(f"**Response from Claude Sonnet 4-6:**\n\n{resp.content}"))


# ### SETUP MEMORY AND TEST MEMORY CREATION

# In[5]:


from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

chat_history = InMemoryChatMessageHistory()
conversation = RunnableWithMessageHistory(llm, lambda session_id: chat_history)
config = {"configurable": {"session_id": "demo"}}


# In[6]:


# Test memory # 1
display(Markdown("**Testing memory with a conversation:**"))
content = conversation.invoke('I\'m studying transformers for NLP, exam Friday', config=config).content
display(Markdown(f"**Claude Sonnet 4-6 response:**\n\n{content}"))


# In[7]:


# Test memory # 2
content1 = conversation.invoke("What am I studying?", config=config).content
display(Markdown(f"**Claude Sonnet 4-6 response:**\n\n{content1}"))


# # SETUP TOOL AND MEMORY TOGETHER

# In[8]:


from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

## Simple decorated calculator function to evaluate simple mathematical expressions
@tool
def calculator(expression: str) -> str:
    """A calculator that can evaluate simple mathematical expressions."""
    try:
        result = str(eval(expression, {"__builtin__": {}}, {}))
        return result
    except Exception as e:
        return f"Error: {str(e)}"

print("\n--- Calculator Test ---\n")
print(calculator("2 + 3 * (4 - 1)"))
print(calculator("10 / 0"))
print(calculator("invalid expression")) 


# In[9]:


## Bind tool to the llm to create a new llm that can use the tool when needed
llm_with_tools = llm.bind_tools([calculator])

# separate history for the tool-enabled conversation so that we can see the difference in responses when the tool is used
tool_history = InMemoryChatMessageHistory()  

# Mapping of tool names to tool functions for the tool-enabled conversation
tools_by_name = {'calculator': calculator}


# In[10]:


def run_react_loop( user_input ):
    # Add user message to history
    tool_history.add_message(HumanMessage(content=user_input))

    while (True):
        # Call LLM with full conversation history
        response = llm_with_tools.invoke(tool_history.messages)

        # history may contain tool use or no tool use. 
        # If tool use, 
        #   the tool response will be added to the history and then the 
        #   loop will continue and call the LLM again with the updated history. 
        # If no tool use, 
        #   then we can break the loop and display the final response.
        tool_history.add_message(response)

        # If no tools were called 
        if not response.tool_calls:
            return response.content

        # Execute each tool call and add the tool response to the history
        for tool_call in response.tool_calls:
            result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            tool_history.add_message(
                ToolMessage(
                    content=str(result),
                    tool_call_id = tool_call["id"] 
                    )
                )
        # LLM can now see the tool response in the updated history and can decide to call more tools or not call any tools and respond to the user.


# In[11]:


response = run_react_loop("What is 12 multiplied by 8?")
display(Markdown(f"**Final Response after tool use:** {response}"))


# In[12]:


response = run_react_loop("I'm studying transformers. How many hours until Friday exam if today is Wednesday and I study 2 hours per day?")
display(Markdown(f"**Response:**\n\n{response}"))


# # MULTITURN CONVERSATION

# In[13]:


turns = ["Hi, I’m studying transformers for NLP, and my exam is on Friday.",
    "Can you suggest a 2-hour study plan for tonight?",
    "If today is Wednesday, how many hours until my exam on Friday if I study 2 hours per day?",
    "What topic am I studying again?",
    "When is my exam?"]


# In[14]:


for msg in turns:
    response = conversation.invoke(msg, config=config).content
    display(Markdown(f"**User:** {msg}\n\n**Claude Sonnet 4-6:** {response}"))

print("\n--- End of Conversation ---\n")


# # STATELESS / MEMORY LESS TEST 

# In[15]:


print("=== STATELESS (no memory) ===")
stateless_llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    temperature=0.2
)

# Turn 1
resp1 = stateless_llm.invoke("I'm studying transformers for NLP, exam Friday")
display(Markdown(f"**Response to Turn 1 from Claude Sonnet 4-6 (Stateless):** {resp1.content}"))

# Turn 2 - model has no memory of Turn 1
resp2 = stateless_llm.invoke("What am I studying?")
display(Markdown(f"**Response to Turn 2 from Claude Sonnet 4-6 (Stateless):** {resp2.content}"))

print("\n=== END STATELESS ===")

