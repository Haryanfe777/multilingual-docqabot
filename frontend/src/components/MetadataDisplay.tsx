import { useTranslation } from 'react-i18next';

interface MetadataDisplayProps {
  metadata: {
    file_name?: string;
    file_type?: string;
    file_size_kb?: number;
    last_modified?: string;
    language?: string;
    [key: string]: any;
  };
}

export default function MetadataDisplay({ metadata }: MetadataDisplayProps) {
  const { t } = useTranslation();
  if (!metadata) return null;
  return (
    <div style={{ margin: '16px 0', color: '#555', border: '1px solid #eee', padding: 12, borderRadius: 6 }}>
      <div><strong>{t('Document')}:</strong> {metadata.file_name}</div>
      <div><strong>{t('Type')}:</strong> {metadata.file_type}</div>
      <div><strong>{t('Size')}:</strong> {metadata.file_size_kb} KB</div>
      <div><strong>{t('Last Modified')}:</strong> {metadata.last_modified}</div>
      {metadata.language && <div><strong>{t('Language')}:</strong> {metadata.language}</div>}
    </div>
  );
} 