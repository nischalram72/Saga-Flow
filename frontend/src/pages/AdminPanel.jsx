import { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState('orders'); // 'orders' or 'inventory'
  
  const [sagas, setSagas] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async (isPolling = false) => {
      try {
        if (!isPolling) {
           setLoading(true);
        }
        setError(null);
        if (activeTab === 'orders') {
          const url = filter === 'ALL' 
            ? 'http://127.0.0.1:8004/sagas' 
            : `http://127.0.0.1:8004/sagas?status=${filter}`;
            
          const response = await axios.get(url);
          setSagas(response.data.sagas || []);
        } else if (activeTab === 'inventory') {
          const response = await axios.get('http://127.0.0.1:8002/products');
          setProducts(response.data || []);
        }
      } catch (err) {
        setError(`Failed to fetch data for ${activeTab}.`);
        console.error(err);
      } finally {
        if (!isPolling) {
           setLoading(false);
        }
      }
    };
    
    fetchData(false);

    // Auto-refresh every 5 seconds
    const intervalId = setInterval(() => fetchData(true), 5000);
    return () => clearInterval(intervalId);
  }, [filter, activeTab]);

  return (
    <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center mb-6 border-b border-gray-200 pb-5">
        <div className="sm:flex-auto">
          <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="mb-6">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => setActiveTab('orders')}
            className={`${activeTab === 'orders' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Sagas & Orders
          </button>
          <button
            onClick={() => setActiveTab('inventory')}
            className={`${activeTab === 'inventory' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Live Inventory
          </button>
        </nav>
      </div>

      {activeTab === 'orders' && (
        <div className="sm:flex sm:items-center mb-4">
          <div className="sm:flex-auto">
            <p className="mt-2 text-sm text-gray-700">
              A comprehensive overview of all orders and their current saga execution status.
            </p>
          </div>
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md border"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">PENDING</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="FAILED">FAILED</option>
              <option value="COMPENSATING">COMPENSATING</option>
            </select>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div className="flex flex-col">
        <div className="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle md:px-6 lg:px-8">
            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg bg-white">
              
              {/* ORDERS TABLE */}
              {activeTab === 'orders' && (
                <table className="min-w-full divide-y divide-gray-300">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Order ID</th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Saga ID</th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Current Step</th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Status</th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Created At</th>
                      <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                        <span className="sr-only">View</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {loading ? (
                      <tr><td colSpan="6" className="py-10 text-center text-gray-500 text-sm">Loading...</td></tr>
                    ) : sagas.length === 0 ? (
                      <tr><td colSpan="6" className="py-10 text-center text-gray-500 text-sm">No orders found.</td></tr>
                    ) : (
                      sagas.map((saga) => (
                        <tr key={saga.saga_id} className="hover:bg-gray-50 transition-colors">
                          <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">{saga.order_id}</td>
                          <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500 font-mono text-xs">{saga.saga_id}</td>
                          <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{saga.current_step}</td>
                          <td className="whitespace-nowrap px-3 py-4 text-sm">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              saga.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                              saga.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                              saga.status === 'COMPENSATING' ? 'bg-orange-100 text-orange-800' :
                              'bg-blue-100 text-blue-800'
                            }`}>
                              {saga.status}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{new Date(saga.created_at).toLocaleString()}</td>
                          <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                            <Link to={`/tracking/${saga.order_id}`} className="text-blue-600 hover:text-blue-900 font-semibold">Audit Trail</Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              )}

              {/* INVENTORY TABLE */}
              {activeTab === 'inventory' && (
                <table className="min-w-full divide-y divide-gray-300">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6">Product ID</th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Available Qty</th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Reserved Qty</th>
                      <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {loading ? (
                      <tr><td colSpan="4" className="py-10 text-center text-gray-500 text-sm">Loading...</td></tr>
                    ) : products.length === 0 ? (
                      <tr><td colSpan="4" className="py-10 text-center text-gray-500 text-sm">No inventory found.</td></tr>
                    ) : (
                      products.map((product) => (
                        <tr key={product.product_id} className="hover:bg-gray-50 transition-colors">
                          <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-6">{product.product_id}</td>
                          <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-900 font-bold">{product.available_qty}</td>
                          <td className="whitespace-nowrap px-3 py-4 text-sm text-orange-600 font-bold">{product.reserved_qty}</td>
                          <td className="whitespace-nowrap px-3 py-4 text-sm">
                            {product.available_qty <= 0 ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Out of Stock</span>
                            ) : product.available_qty < 20 ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Low Stock</span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">In Stock</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              )}
              
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
