import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';

export default function OrderTracking() {
  const { orderId } = useParams();
  const [saga, setSaga] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // 1. Fetch initial state with retries
    const fetchSaga = async (retries = 3) => {
      try {
        const response = await axios.get(`http://127.0.0.1:8004/sagas/${orderId}`);
        if (response.data && response.data.error) {
           if (retries > 0) {
              setTimeout(() => fetchSaga(retries - 1), 1000);
              return;
           } else {
              throw new Error(response.data.error);
           }
        }
        setSaga(response.data);
        setError(null);
      } catch (err) {
        if (retries > 0) {
            setTimeout(() => fetchSaga(retries - 1), 1000);
            return;
        }
        setError("Saga trace not found for this order. It may still be initializing.");
        console.error(err);
      } finally {
        if (retries === 0 || (!error && saga)) {
           setLoading(false);
        }
      }
    };
    fetchSaga();

    // 2. Connect to WebSocket for real-time updates
    const ws = new WebSocket(`ws://127.0.0.1:8004/ws/sagas/${orderId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'SAGA_UPDATE') {
        setSaga(prev => {
          if (!prev) return prev;
          
          // Append new step if it's not already there
          const stepExists = prev.steps.some(s => s.step_name === data.step_name);
          let newSteps = [...prev.steps];
          if (!stepExists) {
            newSteps.push({
              id: Date.now().toString(), // Dummy ID for UI
              step_name: data.step_name,
              status: "SUCCESS",
              created_at: new Date().toISOString()
            });
          }
          
          return {
            ...prev,
            current_step: data.current_step,
            status: data.status,
            steps: newSteps
          };
        });
      }
    };

    return () => {
      ws.close();
    };
  }, [orderId]);

  // Clone saga to not mutate state directly when appending synthetic events
  const displaySaga = saga ? JSON.parse(JSON.stringify(saga)) : null;
  if (displaySaga && displaySaga.status === 'FAILED' && !displaySaga.steps.some(s => s.step_name === 'ORDER_CANCELLED' || s.step_name === 'ORDER_REJECT_REQUESTED')) {
    displaySaga.steps.push({
        id: 'synthetic-fail',
        step_name: 'ORDER_CANCELLED',
        status: 'FAILED',
        created_at: displaySaga.updated_at
    });
  }

  if (loading && !displaySaga) return <div className="p-8 text-center text-gray-500">Loading Saga Trace...</div>;
  if (error && !displaySaga) return <div className="p-8 text-center text-red-500">{error}</div>;

  return (
    <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Saga Execution Trace</h1>
        <Link to="/store" className="text-blue-600 hover:text-blue-800 font-medium">
          &larr; Back to Store
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">Order: {orderId}</h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">Real-time saga execution status.</p>
          </div>
          <div className="text-right">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
              displaySaga.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
              displaySaga.status === 'FAILED' ? 'bg-red-100 text-red-800' :
              displaySaga.status === 'COMPENSATING' ? 'bg-orange-100 text-orange-800' :
              'bg-blue-100 text-blue-800'
            }`}>
              {displaySaga.status}
            </span>
          </div>
        </div>
        
        {/* Visual Step Tracker */}
        <div className="px-6 py-8 border-b border-gray-200">
          <div className="flex items-center justify-between w-full relative">
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-gray-200 z-0"></div>
            
            {/* The active line that fills up */}
            <div 
              className={`absolute left-0 top-1/2 -translate-y-1/2 h-1 z-0 transition-all duration-500 ease-in-out ${displaySaga.status.includes('FAIL') || displaySaga.status.includes('COMPENSAT') ? 'bg-red-500' : 'bg-green-500'}`}
              style={{
                width: 
                  displaySaga.status === 'PENDING' ? '0%' :
                  displaySaga.current_step.includes('INVENTORY') && displaySaga.status === 'PENDING' ? '25%' :
                  displaySaga.current_step === 'PAYMENT_REQUESTED' ? '50%' :
                  displaySaga.current_step === 'PAYMENT_COMPLETED' ? '75%' :
                  displaySaga.status === 'COMPLETED' ? '100%' :
                  displaySaga.status.includes('FAIL') || displaySaga.status === 'COMPENSATING' ? '100%' : '50%'
              }}
            ></div>

            {[
              { id: 'PENDING', label: 'Order Created' },
              { id: 'INVENTORY_RESERVED', label: 'Inventory Reserved' },
              { id: 'PAYMENT_COMPLETED', label: 'Payment Paid' },
              { id: 'COMPLETED', label: 'Completed' }
            ].map((node, i) => {
              // Determine node status
              let nodeStatus = 'pending'; // pending, active, completed, failed
              const stepNames = displaySaga.steps.map(s => s.step_name);
              
              if (displaySaga.status === 'COMPLETED') {
                nodeStatus = 'completed';
              } else if (displaySaga.status === 'FAILED' || displaySaga.status === 'COMPENSATING') {
                if (i === 3) nodeStatus = 'failed';
                else if (i === 2 && stepNames.some(s => s.includes('PAYMENT_FAIL'))) nodeStatus = 'failed';
                else if (i === 1 && stepNames.some(s => s.includes('INVENTORY_FAIL') || s.includes('INVENTORY_RELEASE'))) nodeStatus = 'failed';
                else nodeStatus = 'completed';
              } else {
                if (node.id === 'PENDING') nodeStatus = 'completed';
                else if (node.id === 'INVENTORY_RESERVED' && displaySaga.current_step.includes('PAYMENT')) nodeStatus = 'completed';
                else if (node.id === 'PAYMENT_COMPLETED' && displaySaga.current_step.includes('ORDER_CONFIRMED')) nodeStatus = 'completed';
                else if (displaySaga.current_step.includes(node.id.split('_')[0])) nodeStatus = 'active';
              }

              return (
                <div key={node.id} className="relative z-10 flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 bg-white transition-colors duration-300 ${
                    nodeStatus === 'completed' ? 'border-green-500 text-green-500' :
                    nodeStatus === 'failed' ? 'border-red-500 text-red-500 bg-red-50' :
                    nodeStatus === 'active' ? 'border-blue-500 ring-4 ring-blue-100 text-blue-500' :
                    'border-gray-300 text-gray-300'
                  }`}>
                    {nodeStatus === 'completed' ? (
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                    ) : nodeStatus === 'failed' ? (
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                    ) : (
                      <span className="text-sm font-semibold">{i + 1}</span>
                    )}
                  </div>
                  <span className={`absolute top-10 text-xs font-medium whitespace-nowrap ${
                    nodeStatus === 'completed' ? 'text-green-600' :
                    nodeStatus === 'failed' ? 'text-red-600' :
                    nodeStatus === 'active' ? 'text-blue-600' :
                    'text-gray-500'
                  }`}>
                    {node.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="px-6 py-10 mt-2">
          <ul className="space-y-4">
            {displaySaga.steps.map((step, idx) => {
              const isFailure = step.status === 'FAILED' || step.step_name.includes('FAIL') || step.step_name.includes('REJECT') || step.step_name.includes('RELEASE');
              return (
              <li key={step.id} className="relative pb-4">
                {idx !== displaySaga.steps.length - 1 && (
                  <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true" />
                )}
                <div className="relative flex space-x-3">
                  <div>
                    <span className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${
                      isFailure ? 'bg-red-500' : 'bg-green-500'
                    }`}>
                      <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        {isFailure ? (
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        ) : (
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        )}
                      </svg>
                    </span>
                  </div>
                  <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                    <div>
                      <p className="text-sm text-gray-900 font-medium">{step.step_name}</p>
                    </div>
                    <div className="text-right text-sm whitespace-nowrap text-gray-500">
                      {new Date(step.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}
