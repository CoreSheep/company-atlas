import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import Header from './components/Header'
import FileUpload from './components/FileUpload'
import CSVEditor from './components/CSVEditor'
import S3Config from './components/S3Config'
import { CSVData } from './types'

function App() {
  const [csvData, setCsvData] = useState<CSVData | null>(null)
  const [s3Config, setS3Config] = useState({
    aws_access_key_id: '',
    aws_secret_access_key: '',
    bucket_name: '',
    region_name: 'us-east-1',
  })

  const primaryColor = '#2596be'
  
  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(to bottom, #f5f7fa 0%, #ffffff 100%)' }}>
      <Toaster 
        position="top-right"
        toastOptions={{
          success: {
            style: {
              background: 'rgba(255, 255, 255, 0.95)',
              color: '#1d1d1f',
              backdropFilter: 'blur(20px)',
              borderRadius: '12px',
              border: '1px solid rgba(0, 0, 0, 0.1)',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
            },
            iconTheme: {
              primary: primaryColor,
              secondary: 'white',
            },
          },
        }}
      />
      <Header />
      <main className="container mx-auto px-6 py-12 max-w-7xl">
        {!csvData ? (
          <FileUpload onUpload={setCsvData} />
        ) : (
          <div className="space-y-6">
            <CSVEditor 
              data={csvData} 
              onUpdate={setCsvData}
              onReset={() => setCsvData(null)}
            />
            <S3Config 
              config={s3Config}
              onConfigChange={setS3Config}
              csvData={csvData}
            />
          </div>
        )}
      </main>
    </div>
  )
}

export default App

