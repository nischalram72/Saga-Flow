import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '../context/AuthContext';

export default function OrderCreation() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [quantities, setQuantities] = useState({});
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [error, setError] = useState(null);
  
  // Checkout flow states
  const [checkoutStep, setCheckoutStep] = useState(0); // 0: store, 1: address, 2: payment, 3: confirmed
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');
  const [pincode, setPincode] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [finalOrderId, setFinalOrderId] = useState(null);

  const { token } = useContext(AuthContext);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8002/products');
        setProducts(response.data);
      } catch (err) {
        setError("Failed to load products from Inventory Service.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, []);

  const handleQuantityChange = (productId, qty) => {
    setQuantities({ ...quantities, [productId]: Math.max(0, parseInt(qty) || 0) });
  };

  const calculateTotal = () => {
    let total = 0;
    products.forEach(p => {
      const qty = quantities[p.product_id] || 0;
      total += qty * 50.0;
    });
    return total;
  };

  const getSelectedItems = () => {
    return products
      .filter(p => quantities[p.product_id] > 0)
      .map(p => ({
        product_id: p.product_id,
        quantity: quantities[p.product_id],
        price: 50.0
      }));
  };

  const startCheckout = () => {
    if (getSelectedItems().length === 0) {
      alert("Please select at least one item.");
      return;
    }
    setCheckoutStep(1); // Open Address modal
  };

  const submitOrder = async (method) => {
    setPaymentMethod(method);
    setCheckoutStep(3); // Confirmed modal

    try {
      const payload = {
        user_id: "me", // Backend uses token to resolve user
        total_amount: calculateTotal(),
        items: getSelectedItems(),
        simulate_payment_failure: simulateFailure,
        address,
        phone,
        pincode
      };

      const response = await axios.post('http://127.0.0.1:8001/orders/', payload, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      setFinalOrderId(response.data.id);
      
      // Navigate to tracking page after 2 seconds
      setTimeout(() => {
        navigate(`/tracking/${response.data.id}`);
      }, 2000);
      
    } catch (err) {
      setError(err.response?.data?.detail || "Checkout failed");
      setCheckoutStep(0);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading Storefront...</div>;

  return (
    <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8 relative">
      {/* ADDRESS MODAL */}
      {checkoutStep === 1 && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-md w-full">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Shipping Details</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Address</label>
                <input 
                  type="text" 
                  value={address} onChange={e => setAddress(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500" 
                  placeholder="123 Main St"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Phone Number</label>
                <input 
                  type="text" 
                  value={phone} onChange={e => setPhone(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500" 
                  placeholder="+1 (555) 000-0000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Pincode / ZIP</label>
                <input 
                  type="text" 
                  value={pincode} onChange={e => setPincode(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500" 
                  placeholder="12345"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button onClick={() => setCheckoutStep(0)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md">Cancel</button>
              <button 
                onClick={() => setCheckoutStep(2)} 
                disabled={!address || !phone || !pincode}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                Proceed to Payment
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PAYMENT MODAL */}
      {checkoutStep === 2 && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full text-center">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Select Payment Method</h2>
            
            <div className="space-y-4">
              <button 
                onClick={() => submitOrder('CASH')}
                className="w-full flex items-center justify-center space-x-2 p-4 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition"
              >
                <span className="text-xl font-bold text-gray-700">💵 Pay with Cash</span>
              </button>
              
              <button 
                onClick={() => submitOrder('UPI')}
                className="w-full flex items-center justify-center space-x-2 p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition"
              >
                <span className="text-xl font-bold text-gray-700">📱 Pay with UPI</span>
              </button>
            </div>

            <div className="mt-6">
              <button onClick={() => setCheckoutStep(1)} className="text-sm text-gray-500 hover:text-gray-700">
                &larr; Back to Shipping
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ORDER CONFIRMED MODAL */}
      {checkoutStep === 3 && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-8 rounded-lg shadow-xl max-w-sm w-full text-center transform transition-all scale-100">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-4">
              <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Order Confirmed!</h2>
            <p className="text-gray-500 mb-6">Payment Method: {paymentMethod}</p>
            <p className="text-sm text-gray-400">Redirecting to live tracking...</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow px-5 py-6 sm:px-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Storefront</h1>
          <div className="flex items-center space-x-3 bg-red-50 p-3 rounded-lg border border-red-200">
            <span className="text-sm font-medium text-red-800">Simulate Payment Failure?</span>
            <button 
              onClick={() => setSimulateFailure(!simulateFailure)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${simulateFailure ? 'bg-red-600' : 'bg-gray-300'}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${simulateFailure ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
          </div>
        </div>
        
        {error && (
          <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => (
            <div key={product.product_id} className="border rounded-lg p-4 shadow-sm hover:shadow-md transition">
              <h3 className="text-lg font-medium text-gray-900">{product.product_id}</h3>
              <p className="text-gray-500 text-sm mt-1">Available: {product.available_qty}</p>
              <p className="text-gray-800 font-bold mt-2">$50.00</p>
              
              <div className="mt-4 flex items-center space-x-3">
                <label className="text-sm text-gray-600">Qty:</label>
                <input 
                  type="number" 
                  min="0"
                  max={product.available_qty}
                  value={quantities[product.product_id] || ''}
                  onChange={(e) => handleQuantityChange(product.product_id, e.target.value)}
                  className="w-20 border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-2 border"
                  placeholder="0"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 border-t pt-6 flex justify-between items-center">
          <div className="text-2xl font-bold text-gray-900">
            Total: ${calculateTotal().toFixed(2)}
          </div>
          <button 
            onClick={startCheckout}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition shadow-md"
          >
            Checkout
          </button>
        </div>
      </div>
    </div>
  );
}
