# Agentic Inventory & Finance Orchestration

This project demonstrates a multi-agent system using the **OpenAI Agents SDK**. It features two autonomous agents collaborating to maintain a warehouse.

## Agents
1. **Inventory Agent**: Monitors stock levels. If an item falls below its threshold, it automatically creates a Purchase Order (PO) and hands off the conversation to the Finance Agent.
2. **Finance Agent**: Reviews the PO, checks the budget, and either approves or rejects the request. On approval, it updates the finance records and simulates a stock delivery.

## Project Structure
- `database.py`: SQLite setup for inventory and finance tables.
- `agent_definitions.py`: Definitions for tools, agents, and handoff logic.
- `main.py`: The entry point that runs the agentic simulation.

## Getting Started
1. **Install Dependencies**:
   ```bash
   pip install openai-agents python-dotenv
   ```
2. **Setup API Key**:
   Create a `.env` file in this directory and add your key:
   ```
   OPENAI_API_KEY=your_sk_key_here
   ```
3. **Run the Simulation**:
   ```bash
   python main.py
   ```

## Scenario
The simulation starts with:
- **Monitors**: 3 in stock (Threshold: 5).
- **Task**: The Inventory Agent is told that 1 more monitor was shipped. It detects the low stock (2 units), creates a PO, and hands off to Finance to approve the restock.
