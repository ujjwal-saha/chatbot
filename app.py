from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Annotated
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage
import sqlite3
import uuid
import streamlit as st


connection=sqlite3.connect(database='chatbot.db',check_same_thread=False)
checkpointer = SqliteSaver(conn=connection)
config = {"configurable": {"thread_id": "1"}}

class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)
llm=ChatOpenAI(temperature=0.7, api_key=st.secrets["OPENAI_API_KEY"])

def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

graph = graph_builder.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads=set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)  


#--------------------- Utility Functions ----------------

def generate_thread_id():
    return uuid.uuid4()

def reset_chat():
    thread_id=generate_thread_id()
    st.session_state['thread_id']=thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history']=[]

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    return graph.get_state(config={"configurable": {"thread_id": thread_id}}).values.get('messages', [])   

#-------------------- Session Setup -----------------

if 'message_history' not in st.session_state:
    st.session_state['message_history']=[]

if 'thread_id' not in st.session_state:
    st.session_state['thread_id']=generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads']=retrieve_all_threads()

add_thread(st.session_state['thread_id'])

#-------------------- Side bar -----------------------

st.sidebar.title("Chatbot")
if st.sidebar.button("New Chat"):
    reset_chat()
st.sidebar.write("My Conversations")
index=0
for thread_id in st.session_state['chat_threads']:
  index+=1
  if st.sidebar.button(f"Conversation{index}",key={thread_id}):
      st.session_state['thread_id']=thread_id
      messages=load_conversation(thread_id)
      temp_msg=[]
      for msg in messages:
          if isinstance(msg,HumanMessage):
              role='user'
          else:
              role='assistant'
          temp_msg.append({'role':role,'content':msg.content}) 
      st.session_state['message_history']=temp_msg   

     
#-------------------------- Main UI ----------------------

st.title("Chatbot")

for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])


user_input=st.chat_input('Type here')

if user_input:
    st.session_state['message_history'].append({'role':'user','content':user_input})
    with st.chat_message('user'):
        st.text(user_input)

    #response=graph.invoke({'messages':HumanMessage(content=user_input)},config=CONFIG)
    #ai_message=response['messages'][-1].content
    #st.session_state['message_history'].append({'role':'assistant','content':ai_message})
    CONFIG={"configurable": {"thread_id": st.session_state['thread_id']}}
    with st.chat_message('assistant'):
       ai_message= st.write_stream(
            message_chunk.content for message_chunk, metadata in graph.stream(
                {'messages':[HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages' 
            )

        )
       #st.text(ai_message)
    st.session_state['message_history'].append({'role':'assistant','content':ai_message}) 



         
