import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { displayBookingReference } from '../utils/eventTitle';

function loadRazorpayCheckout() {
  if (window.Razorpay) return Promise.resolve(true);
  return new Promise((resolve) => {
    const existing = document.querySelector('script[data-razorpay-checkout]');
    if (existing) {
      existing.addEventListener('load', () => resolve(true), { once: true });
      existing.addEventListener('error', () => resolve(false), { once: true });
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.dataset.razorpayCheckout = 'true';
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

function PaymentButton({ booking, onVerified }) {
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const beginPayment = async () => {
    setPaying(true);
    setError('');
    setMessage('');
    try {
      const scriptReady = await loadRazorpayCheckout();
      if (!scriptReady || !window.Razorpay) {
        throw new Error('Razorpay Checkout could not be loaded. Check your connection and retry.');
      }

      const orderResponse = await api.post('/payments/create-order/', {
        booking_id: booking.id,
      });
      const order = orderResponse.data;
      const checkout = new window.Razorpay({
        key: order.key,
        amount: order.amount,
        currency: order.currency,
        name: 'EventEase',
        description: `Booking ${displayBookingReference(order.booking_reference)}`,
        order_id: order.order_id,
        modal: {
          ondismiss: () => {
            setMessage('Payment was cancelled. Your booking remains pending; you can retry or cancel it.');
            setPaying(false);
          },
        },
        handler: async (checkoutResponse) => {
          try {
            const verification = await api.post('/payments/verify/', {
              razorpay_order_id: checkoutResponse.razorpay_order_id,
              razorpay_payment_id: checkoutResponse.razorpay_payment_id,
              razorpay_signature: checkoutResponse.razorpay_signature,
            });
            if (verification.data.status !== 'SUCCESS') {
              throw new Error('The server has not verified this payment.');
            }
            onVerified?.(verification.data);
            navigate('/tickets', {
              state: {
                bookingReference: order.booking_reference,
                bookingStatus: verification.data.booking_status,
              },
            });
          } catch (verificationError) {
            setError(
              verificationError.response?.data?.error ||
              verificationError.message ||
              'Payment could not be verified. Do not retry until the payment status is checked.',
            );
            setPaying(false);
          }
        },
        theme: { color: '#6d28d9' },
      });

      checkout.on('payment.failed', (failure) => {
        setError(failure.error?.description || 'Payment was not completed. You can retry this booking.');
        setPaying(false);
      });
      checkout.open();
    } catch (paymentError) {
      setError(
        paymentError.response?.data?.error ||
        paymentError.message ||
        'Could not start payment. Please retry.',
      );
      setPaying(false);
    }
  };

  return (
    <div className="payment-control">
      <button className="btn btn-primary" onClick={beginPayment} disabled={paying}>
        {paying ? 'Preparing secure checkout…' : `Pay ₹${booking.total_amount}`}
      </button>
      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="payment-message" role="status">{message}</p>}
    </div>
  );
}

export default PaymentButton;

