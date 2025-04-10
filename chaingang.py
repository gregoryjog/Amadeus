from langchain.memory import ZepMemory
import langchain
from openai import OpenAIError, BadRequestError, AuthenticationError, RateLimitError, APIError
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_community.retrievers import ZepRetriever
from langchain_community.retrievers.zep import SearchScope
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from langchain.tools.retriever import create_retriever_tool
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.vectorstores.zep import ZepVectorStore
from langchain_community.embeddings import CohereEmbeddings, OpenAIEmbeddings
import openai
from openai import OpenAIError

class Amadeus:
    def __init__(
            self,
            config,
            added_tools=None,
            verbose=False,
    ):
        self.session_id = config.get('session_id')
        self.zep_api_port = config.get('zep_api_port') if config.get('zep_api_port') else 8000
        self.zep_api_url = f"{config.get('zep_api_url')}:{str(self.zep_api_port)}"
        self.roleplay_template = config.get('prompt')
        self.openai_api_key = config.get('openai_api_key')
        self.cohere_api_key = config.get('cohere_api_key')
        self.qdrant_api_url = config.get('qdrant_api_url')
        self.qdrant_api_port = config.get('qdrant_api_port') if config.get('qdrant_api_port') else 6333
        self.model_name = config.get('model')
        self.temperature = config.get('temperature')
        self.verbose = verbose
        self.added_tools = added_tools if added_tools is not None else []
        self.retriever = ZepRetriever(
            url=self.zep_api_url,
            session_id=self.session_id,
            top_k=5,
            search_scope=SearchScope.summary
        )
        self.memory = ZepMemory(
            url=self.zep_api_url,
            session_id=self.session_id,
            memory_key="history",
            input_key="input"
        )
        self.embeddings = CohereEmbeddings(cohere_api_key=self.cohere_api_key, model='embed-english-v3.0')
        self.qclient = QdrantClient(self.qdrant_api_url, port=6333, prefer_grpc=True)
        self.qdrant = Qdrant(
            client=self.qclient,
            embeddings=self.embeddings,
            collection_name='previousSessions',

        ).as_retriever()
        self.glossary_search_tool = create_retriever_tool(
            self.qdrant,
            "search_glossary",
            "Provides information for all events and character information previously established in past sessions."
        )
        self.vectorstore = ZepVectorStore(
            collection_name="characters",  # Rework this
            api_url=self.zep_api_url,
        ),
        self.backlog_retriever = ZepVectorStore(
            collection_name="backlog",
            api_url=self.zep_api_url,
        ).as_retriever(search_type='mmr',search_kwargs={"k": 5})

        self.tool = create_retriever_tool(
            self.retriever,
            "memory_search",
            "Search for recently established events and dialogue backlog"
        )
        self.tools = [
            self.tool
        ]
        # self.tools.extend(self.added_tools)
        self.prompt = PromptTemplate(
            input_variables=["history", "input", "agent_scratchpad"],
            template=self.roleplay_template
        )
        self.openai = ChatOpenAI(
            openai_api_key=self.openai_api_key,
            temperature=self.temperature,
            model_name=self.model_name
        )
        self.agent = OpenAIFunctionsAgent(
            llm=self.openai,
            tools=self.tools,
            prompt=self.prompt
        )
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=self.verbose,
            memory=self.memory,
            max_iterations=5
        )

    def invoke(self, user_input):
        try:
            return self.agent_executor.run(user_input)
        except langchain.errors.OutputParserException:
            return "I'm having trouble understanding how to respond. Could you rephrase that?"
        except RateLimitError:
            return "I'm currently experiencing high demand. Please try again in a moment."
        except BadRequestError:
            return "I couldn't process that request properly. Please try again."
        except AuthenticationError:
            return "I'm having trouble authenticating with my knowledge base. Please check my configuration."
        except APIError:
            return "I'm having trouble connecting to my knowledge base. Please try again shortly."
        except OpenAIError as e:
            print(f"OpenAI API error: {str(e)}")
            return "I encountered an issue with my AI services. Please try again."
        except Exception as e:
            print(f"Error in Amadeus.invoke: {str(e)}")
            return "I apologize, but I encountered an unexpected error. Please try again."
