export default function Loader() {
  return (
    <div style={{ textAlign: 'center', margin: '24px 0' }}>
      <div className="loader" style={{ display: 'inline-block', width: 32, height: 32, border: '4px solid #eee', borderTop: '4px solid #222', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
} 