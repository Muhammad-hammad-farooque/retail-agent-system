import AgentChat from '@/components/AgentChat';
import { Bot, Zap } from 'lucide-react';

export default function AgentPage() {
  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b border-gray-100 bg-white px-8 py-5 shrink-0">
        <div className="flex items-center gap-3">
          <div className="bg-blue-100 p-2 rounded-xl">
            <Bot className="w-6 h-6 text-blue-700" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">AI Agent</h1>
            <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5">
              <Zap className="w-3 h-3" />
              Powered by OpenAI GPT-4o · 5 specialist agents
            </p>
          </div>
        </div>

        <div className="mt-4 flex gap-6 text-xs text-gray-500">
          {['Inventory', 'Accounting', 'Customer Service', 'Marketing'].map((a) => (
            <span key={a} className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              {a} Agent
            </span>
          ))}
        </div>
      </div>

      {/* Chat */}
      <div className="flex-1 min-h-0 bg-white">
        <AgentChat />
      </div>
    </div>
  );
}
