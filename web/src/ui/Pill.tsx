interface PillProps {
  bucket: string;
}

export function Pill({ bucket }: PillProps) {
  const getBucketClass = (bucket: string) => {
    switch (bucket) {
      case 'low':
        return 'low';
      case 'medium':
        return 'medium';
      case 'high':
        return 'high';
      case 'critical':
        return 'critical';
      default:
        return '';
    }
  };

  return (
    <span className={`pill ${getBucketClass(bucket)}`}>
      {bucket}
    </span>
  );
}
