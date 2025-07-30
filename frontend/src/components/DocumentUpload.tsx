import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

export default function DocumentUpload({ onUpload }: { onUpload: (file: File) => void }) {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = () => {
    if (selectedFile) {
      onUpload(selectedFile);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <button
        className="upload-btn"
        onClick={() => fileInputRef.current?.click()}
        type="button"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="none" viewBox="0 0 24 24"><path fill="currentColor" d="M12 16V4m0 0l-4 4m4-4l4 4" stroke="#a259e6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><rect x="4" y="16" width="16" height="4" rx="2" fill="#a259e6" opacity="0.2"/></svg>
        {t('Upload Document')}
      </button>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
      {selectedFile && (
        <div style={{ color: '#a7a9be', marginTop: 8, fontSize: 14 }}>{selectedFile.name}</div>
      )}
      <button
        onClick={handleUpload}
        disabled={!selectedFile}
        style={{
          marginTop: 12,
          background: '#a259e6',
          color: '#fff',
          border: 'none',
          borderRadius: 12,
          padding: '10px 28px',
          fontWeight: 600,
          fontSize: 16,
          cursor: !selectedFile ? 'not-allowed' : 'pointer',
          opacity: !selectedFile ? 0.5 : 1,
        }}
      >
        {t('Upload Document')}
      </button>
    </div>
  );
} 