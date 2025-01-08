<p align="center">
<img src="src/img/bio3_logo_with_bg.png">
<br>
<em>Biosphere3</em>
<br><br>
<a title="Build Status" target="_blank" href="#"><img src="https://img.shields.io/badge/Build_Status-passing-green"></a>
<a title="Releases" target="_blank" href="#"><img src="https://img.shields.io/badge/Releases-V0.1-blue"></a>
<a title="Downloads" target="_blank" href="#"><img src="https://img.shields.io/badge/Downloads-873-purple"></a>

<br>
<a title="Docker Pulls" target="_blank" href="#"><img src="https://img.shields.io/badge/Docker_Pulls-green"></a>
<a title="Docker Image Size" target="_blank" href="#"><img src="https://img.shields.io/badge/Docker_Image_Size-ff96b4"></a>
<a title="Hits" target="_blank" href="#"><img src="https://img.shields.io/badge/Hits-lightgrey"></a>
<br>
<a title="AGPLv3" target="_blank" href="#"><img src="https://img.shields.io/badge/license-AGPLv3-orange"></a>
<a title="Code Size" target="_blank" href="#"><img src="https://img.shields.io/badge/Code_Size-yellow"></a>
<a title="GitHub Pull Requests" target="_blank" href="#"><img src="https://img.shields.io/badge/GitHub_Pull_Requests-FF9966"></a>
<br>
<a title="GitHub Commits" target="_blank" href="#"><img src="https://img.shields.io/badge/GitHub_Commits-lightgrey"></a>
<a title="Last Commit" target="_blank" href="#"><img src="https://img.shields.io/badge/Last_Commit-FF9900"></a>
<br><br>
</p>

---

## Table of Contents

* [👾 Introduction](#-introduction)
* [🔮 Features](#-features)
* [🏗️ Architecture and Ecosystem](#-architecture-and-ecosystem)
* [🌟 Star History](#-star-history)
* [🗺️ Roadmap](#️-roadmap)
* [🏘️ Community](#️-community)
* [🛠️ Development Guide](#️-development-guide)
* [❓ FAQ](#-faq)
* [🙏 Acknowledgement](#-acknowledgement)
  * [Contributors](#contributors)

---

## 👾 Introduction
 
🎮 **Biosphere3** is a **Massive Multi-Agent Online Game** that merges elements of the 🏙️ *Stanford Town Simulator* with 🏡 *The Sims*. In this game, players interact with **Sovereignty Agents** 🤖—intelligent, autonomous entities (also known as **Digital Lifeforms**)—by establishing bounded relationships through conversation 🗨️, rather than direct control. Together with these agents, players co-govern a 🌐 dynamic, autonomous, and self-sustaining society.

💡 **Key Innovation**: The core of Biosphere3 lies in the creation of **Sovereignty Agents**, who possess:
- 💵 **Economic Independence**: They can manage their own assets and engage in blockchain-based activities.
- 🛠️ **Self-Governance**: Sovereignty Agents make decisions and evolve based on interactions.
- 🧠 **Adaptive Intelligence**: They meaningfully interact with both humans and other agents, pushing the boundaries of AI autonomy.

🌟 **More Than a Game**: Biosphere3 is a **social simulation** and experimental platform designed to analyze interactions between:
- 👥 **Humans and Agents**
- 🤖 **Agents and Other Agents**

Through these interactions, we aim to refine our algorithms 🔄 and explore the future of harmonious and efficient coexistence 🌍 between humans and AI in decentralized digital societies.

🚀 Join us in pioneering the next frontier of AI-driven virtual worlds and witness the evolution of **Sovereignty Agents** as the foundation for tomorrow’s digital ecosystems.

## 🔮 Features
Our latest version of code for the **Sovereignty Agents** is in the `core` path. There are seven main modules: 

- 📞 **Message Center**,
- 🧩 **Model Selector**,
- 🗓️ **Action Planner**,
- 💬 **Conversation**,
- 📊 **Database Support**,
- 🦸‍♂️ **Character Manager**,
- ⚙️ **Game Settings**.
  
The main functions and file path of these seven modules are listed as follows.    
Old versions and other experiment data can be found in the `legacy` path. Interested developers can learn about our development journey from this path.

Module Name | Description | File Path
---- | ---- | ----
📞 Message Center | <ul><li> Receive response messages from the game server and send agent decisions to the game environment for both plan and conversation workflow through websocket connections.</li></ui> | <ul><li>`core/ai.py`</li></ui>
🧩 Model Selector | <ul><li>Select different model types, and split api keys for plan and conversation module.</li></ui> | <ul><li>`core/llm_factory.py`</li></ui>
🗓️ Action Planner | <ul><li>Create an agent instance and run the planning workflow. </li><li> Get character data from database. </li><li> Prompt for the agent instance. </li><li> Construct output structures for the agent instance. </li><li> Invoke the LLM for each plan function of the agent instance.</li></ui> | <ul><li>`core/graph_instance.py` </li><li> `core/agent_srv/utils.py` </li><li> `core/agent_srv/prompts.py` </li><li> `core/agent_srv/node_models.py` </li><li> `core/agent_srv/node_engines.py`</li></ui>
💬 Conversation | <ul><li>Create an conversation instance and run different tasks. </li><li> Prompt for the conversation instance. </li><li> Construct output structures for the conversation instance. </li><li> Invoke the LLM for launching, reponding and reading tasks. </li><li> Create conversation planner and responser.</li></ui> | <ul><li>`core/conversation_instance.py` </li><li> `core/conversation_srv/conversation_prompts.py` </li><li> `core/conversation_srv/conversation_model.py` </li><li> `core/conversation_srv/conversation_engines.py` </li><li> `core/conversation_srv/conversation_utils.py`</li></ui> 
📊 Database Support | <ul><li>Fetch character data from game database and update new states. </li><li> Get agent data from agent database and update agent decisions.</li></ui> | <ul><li>`core/db/game_api_utils.py` </li><li> `core/db/database_api_utils.py`</li></ui>
🦸‍♂️ Character Manager | <ul><li>Manage and monitor all active agent connections and clean up disconnected characters.</li></ui> | <ul><li>`core/websocket_server`</li></ui> 
⚙️ Game Settings | <ul><li>Map character skills to actions.</li></ui> | <ul><li>`core/files/skill2actions.json`</li></ui>
💾 Experiments | <ul><li>Old versions and other experiments during the development process.</li></ui> | <ul><li>`legacy`</li></ui>


## 🛠️ Quickstart
### Overview
Our project consists of multiple components, including **databases and game environment**. To provide a seamless experience for developers and researchers who want to quickly get started with our **Agent framework**, we’ve designed a **simulator** that replicates the core functionalities of both the game and database environments.

This **lightweight sandbox environment** allows you to test and interact with the Agent framework in a controlled setting without requiring full integration with the actual game and databases. However, note that **some features are limited**, and full capabilities can only be experienced when connected to the complete game environment.

### Prerequisites
Before running the simulator, ensure that you have:
- Python 3.10 or above installed.
- All required dependencies installed via pip.
- A properly configured .env file with necessary API keys and database URLs.

### Setup Instructions
1. Install Dependencies
```bash
pip install -r requirements.txt
```

2. Configure Environment Variables
```bash
cp .env.example .env
```
- Add the necessary API keys
- Add database URLs, if you run locally:
```
GAME_BACKEND_URL="http://127.0.0.1:5003"
AGENT_BACKEND_URL="http://127.0.0.1:5006"
GAME_BACKEND_TIMEOUT=8
```

3. Run the Websocket server
```bash
python core/ai.py
```

4. Open another terminal & Run the game simulators
```bash
sh run_simulator.sh
```

5. Interact with the Agent
- Once running, you can observe the Agent’s behavior in the terminal.

**You can refer to our [official website](https://biosphere3.ai/) for more information and demo.**
