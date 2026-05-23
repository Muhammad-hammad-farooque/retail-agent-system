import AgentChat from '@/components/AgentChat';
import { Bot } from 'lucide-react';

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
            <p className="text-xs text-gray-500 mt-0.5">Intelligent Retail System</p>
          </div>
        </div>
      </div>

      {/* Chat */}
      <div className="flex-1 min-h-0 bg-white">
        <AgentChat />
      </div>
    </div>
  );
}
