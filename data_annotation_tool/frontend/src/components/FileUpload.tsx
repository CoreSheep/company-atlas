import { useState, useRef } from 'react'
import { Upload, FileText, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import apiClient from '../api/client'
import { CSVData } from '../types'

interface FileUploadProps {
  onUpload: (data: CSVData) => void
}

const FileUpload = ({ onUpload }: FileUploadProps) => {
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.csv')) {
      toast.error('Please upload a CSV file')
      return
    }

    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await apiClient.post('/files/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      toast.success('File uploaded successfully!')
      onUpload(response.data)
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to upload file'
      toast.error(errorMessage)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.name.endsWith('.csv')) {
      const fakeEvent = {
        target: { files: [file] },
      } as any
      handleFileSelect(fakeEvent)
    } else {
      toast.error('Please drop a CSV file')
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div
        className="rounded-2xl p-16 text-center transition-all duration-300 cursor-pointer"
        style={{
          background: 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(20px)',
          border: '2px dashed rgba(37, 150, 190, 0.2)',
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'rgba(37, 150, 190, 0.4)'
          e.currentTarget.style.boxShadow = '0 8px 32px rgba(37, 150, 190, 0.12)'
          e.currentTarget.style.transform = 'translateY(-2px)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'rgba(37, 150, 190, 0.2)'
          e.currentTarget.style.boxShadow = '0 4px 24px rgba(0, 0, 0, 0.06)'
          e.currentTarget.style.transform = 'translateY(0)'
        }}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          {isUploading ? (
            <div className="flex flex-col items-center gap-6">
              <Loader2 className="w-14 h-14 animate-spin" style={{ color: '#2596be' }} />
              <p className="text-lg font-medium tracking-tight" style={{ color: '#1d1d1f' }}>
                Uploading...
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-6">
              <div 
                className="p-5 rounded-2xl transition-all duration-300"
                style={{ 
                  background: 'linear-gradient(135deg, rgba(37, 150, 190, 0.1) 0%, rgba(37, 150, 190, 0.05) 100%)',
                  border: '1px solid rgba(37, 150, 190, 0.15)'
                }}
              >
                <Upload className="w-12 h-12" style={{ color: '#2596be' }} />
              </div>
              <div>
                <p className="text-xl font-semibold tracking-tight mb-2" style={{ color: '#1d1d1f' }}>
                  Click to upload or drag and drop
                </p>
                <p className="text-sm" style={{ color: '#86868b' }}>
                  CSV files only (Max 10MB)
                </p>
              </div>
            </div>
          )}
        </label>
      </div>

      <div 
        className="mt-8 rounded-2xl p-5 transition-all duration-300"
        style={{ 
          background: 'rgba(255, 255, 255, 0.6)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(37, 150, 190, 0.15)',
          boxShadow: '0 2px 16px rgba(0, 0, 0, 0.04)'
        }}
      >
        <div className="flex items-start gap-4">
          <div 
            className="p-2 rounded-lg flex-shrink-0"
            style={{ 
              background: 'linear-gradient(135deg, rgba(37, 150, 190, 0.1) 0%, rgba(37, 150, 190, 0.05) 100%)'
            }}
          >
            <FileText className="w-5 h-5" style={{ color: '#2596be' }} />
          </div>
          <div className="text-sm flex-1">
            <p className="font-semibold mb-2 tracking-tight" style={{ color: '#1d1d1f' }}>
              Supported Features:
            </p>
            <ul className="space-y-1.5" style={{ color: '#86868b' }}>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#2596be' }}></span>
                Upload CSV files up to 10MB
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#2596be' }}></span>
                Edit data in a user-friendly table interface
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#2596be' }}></span>
                Save edited files locally
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#2596be' }}></span>
                Upload directly to AWS S3
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileUpload

