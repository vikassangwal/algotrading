import React, { useState } from 'react';

const routines = {
  daily: [
    { id: 'd1', task: 'Check economic calendar for high-impact news', completed: false },
    { id: 'd2', task: 'Review overnight market action and major levels', completed: false },
    { id: 'd3', task: 'Identify top 3 potential setups for the day', completed: false },
    { id: 'd4', task: 'Ensure trading platform and charts are set up', completed: false },
    { id: 'd5', task: 'Post-market: Journal all taken trades', completed: false },
  ],
  weekly: [
    { id: 'w1', task: 'Review all weekly trades and calculate win rate/R-multiple', completed: false },
    { id: 'w2', task: 'Identify biggest mistake of the week and how to avoid it', completed: false },
    { id: 'w3', task: 'Analyze higher timeframe charts (Weekly/Daily) for next week', completed: false },
    { id: 'w4', task: 'Set specific goals for the upcoming week', completed: false },
  ],
  monthly: [
    { id: 'm1', task: 'Calculate monthly P&L and performance metrics', completed: false },
    { id: 'm2', task: 'Review trading plan and determine if any adjustments are needed', completed: false },
    { id: 'm3', task: 'Assess psychological state and emotional discipline', completed: false },
    { id: 'm4', task: 'Withdraw profits or adjust capital allocation', completed: false },
  ]
};

const TradingRoutines = () => {
  const [activeRoutine, setActiveRoutine] = useState('daily');
  const [tasks, setTasks] = useState(routines);

  const toggleTask = (routineType, taskId) => {
    setTasks(prevTasks => {
      const newRoutine = prevTasks[routineType].map(task => 
        task.id === taskId ? { ...task, completed: !task.completed } : task
      );
      return { ...prevTasks, [routineType]: newRoutine };
    });
  };

  const currentTasks = tasks[activeRoutine];
  const progress = Math.round((currentTasks.filter(t => t.completed).length / currentTasks.length) * 100);

  return (
    <div className="max-w-3xl mx-auto p-6 md:p-8 bg-white rounded-xl shadow-lg mt-10 border border-gray-100">
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Trading Routines</h1>
      <p className="text-gray-500 mb-8">Maintain consistency with structured reviews.</p>

      <div className="flex space-x-1 border-b border-gray-200 mb-8 overflow-x-auto">
        {['daily', 'weekly', 'monthly'].map(routine => (
          <button
            key={routine}
            className={`px-6 py-3 font-medium capitalize transition-colors duration-200 focus:outline-none whitespace-nowrap ${
              activeRoutine === routine
                ? 'border-b-2 border-indigo-600 text-indigo-600'
                : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
            }`}
            onClick={() => setActiveRoutine(routine)}
          >
            {routine} Review
          </button>
        ))}
      </div>

      <div className="mb-8">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-600">Completion Progress</span>
          <span className="text-sm font-bold text-indigo-600">{progress}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
          <div 
            className="bg-indigo-600 h-2.5 rounded-full transition-all duration-500 ease-out" 
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      </div>

      <div className="space-y-3">
        {currentTasks.map(task => (
          <div 
            key={task.id} 
            className={`flex items-start p-4 rounded-xl border-2 cursor-pointer transition-all duration-200 group ${
              task.completed 
                ? 'bg-indigo-50/50 border-indigo-200 hover:border-indigo-300' 
                : 'bg-white border-gray-100 hover:border-indigo-100 hover:shadow-sm'
            }`}
            onClick={() => toggleTask(activeRoutine, task.id)}
          >
            <div className="flex-shrink-0 mt-0.5 relative">
              <input 
                type="checkbox" 
                className="w-5 h-5 text-indigo-600 bg-white border-gray-300 rounded focus:ring-indigo-500 focus:ring-offset-0 cursor-pointer transition-colors"
                checked={task.completed}
                readOnly
              />
            </div>
            <div className="ml-4 flex-1">
              <span className={`text-base transition-colors duration-200 ${
                task.completed ? 'line-through text-gray-400' : 'text-gray-700 group-hover:text-gray-900'
              }`}>
                {task.task}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TradingRoutines;
