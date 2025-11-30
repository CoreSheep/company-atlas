import { useState } from 'react'
import { Cloud, CheckCircle, XCircle, Upload, Settings } from 'lucide-react'
import toast from 'react-hot-toast'
import apiClient from '../api/client'
import { CSVData, S3Config as S3ConfigType } from '../types'

interface S3ConfigProps {
  config: S3ConfigType
  onConfigChange: (config: S3ConfigType) => void
  csvData: CSVData
}

const S3Config = ({ config, onConfigChange, csvData }: S3ConfigProps) => {
  const [isTesting, setIsTesting] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [s3Key, setS3Key] = useState(csvData.filename)

  const handleInputChange = (field: keyof S3ConfigType, value: string) => {
    onConfigChange({ ...config, [field]: value })
    setConnectionStatus('idle')
  }

  const handleTestConnection = async () => {
    setIsTesting(true)
    setConnectionStatus('idle')
    try {
      await apiClient.post('/s3-config/test_connection/', config)
      setConnectionStatus('success')
      toast.success('S3 connection successful!')
    } catch (error: any) {
      setConnectionStatus('error')
      const errorMessage = error.response?.data?.error || 'Connection test failed'
      toast.error(errorMessage)
    } finally {
      setIsTesting(false)
    }
  }

  const handleUploadToS3 = async () => {
    if (!config.aws_access_key_id || !config.aws_secret_access_key || !config.bucket_name) {
      toast.error('Please configure S3 settings first')
      return
    }

    if (connectionStatus !== 'success') {
      toast.error('Please test the connection first')
      return
    }

    setIsUploading(true)
    try {
      const response = await apiClient.post('/files/upload_to_s3/', {
        ...config,
        filename: csvData.filename,
        headers: csvData.headers,
        rows: csvData.rows,
        s3_key: s3Key,
      })

      toast.success('File uploaded to S3 successfully!')
      console.log('S3 URL:', response.data.s3_url)
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to upload to S3'
      toast.error(errorMessage)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200">
      <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg" style={{ backgroundColor: '#2596be1a' }}>
              <Cloud className="w-6 h-6" style={{ color: '#2596be' }} />
            </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">AWS S3 Configuration</h2>
            <p className="text-sm text-gray-500 mt-1">Configure and upload to S3</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AWS Access Key ID
            </label>
            <input
              type="text"
              value={config.aws_access_key_id}
              onChange={(e) => handleInputChange('aws_access_key_id', e.target.value)}
              placeholder="AKIAIOSFODNN7EXAMPLE"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-transparent transition-all"
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#2596be'
                e.currentTarget.style.boxShadow = '0 0 0 2px #2596be40'
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = '#d1d5db'
                e.currentTarget.style.boxShadow = 'none'
              }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AWS Secret Access Key
            </label>
            <input
              type="password"
              value={config.aws_secret_access_key}
              onChange={(e) => handleInputChange('aws_secret_access_key', e.target.value)}
              placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-transparent transition-all"
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#2596be'
                e.currentTarget.style.boxShadow = '0 0 0 2px #2596be40'
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = '#d1d5db'
                e.currentTarget.style.boxShadow = 'none'
              }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              S3 Bucket Name
            </label>
            <input
              type="text"
              value={config.bucket_name}
              onChange={(e) => handleInputChange('bucket_name', e.target.value)}
              placeholder="my-bucket-name"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-transparent transition-all"
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#2596be'
                e.currentTarget.style.boxShadow = '0 0 0 2px #2596be40'
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = '#d1d5db'
                e.currentTarget.style.boxShadow = 'none'
              }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              AWS Region
            </label>
            <select
              value={config.region_name}
              onChange={(e) => handleInputChange('region_name', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-transparent transition-all"
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#2596be'
                e.currentTarget.style.boxShadow = '0 0 0 2px #2596be40'
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = '#d1d5db'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <option value="us-east-1">US East (N. Virginia)</option>
              <option value="us-east-2">US East (Ohio)</option>
              <option value="us-west-1">US West (N. California)</option>
              <option value="us-west-2">US West (Oregon)</option>
              <option value="eu-west-1">Europe (Ireland)</option>
              <option value="eu-central-1">Europe (Frankfurt)</option>
              <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
              <option value="ap-southeast-2">Asia Pacific (Sydney)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            S3 Key (File Path)
          </label>
          <input
            type="text"
            value={s3Key}
            onChange={(e) => setS3Key(e.target.value)}
            placeholder="path/to/file.csv"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:border-transparent transition-all"
            onFocus={(e) => {
              e.currentTarget.style.borderColor = '#2596be'
              e.currentTarget.style.boxShadow = '0 0 0 2px #2596be40'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = '#d1d5db'
              e.currentTarget.style.boxShadow = 'none'
            }}
          />
          <p className="text-xs text-gray-500 mt-1">
            The path where the file will be stored in S3
          </p>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={handleTestConnection}
            disabled={isTesting || !config.aws_access_key_id || !config.aws_secret_access_key || !config.bucket_name}
            style={{ backgroundColor: '#2596be' }}
            className="flex items-center gap-2 px-6 py-3 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            onMouseEnter={(e) => {
              if (!e.currentTarget.disabled) {
                e.currentTarget.style.backgroundColor = '#1a7a9a'
              }
            }}
            onMouseLeave={(e) => {
              if (!e.currentTarget.disabled) {
                e.currentTarget.style.backgroundColor = '#2596be'
              }
            }}
          >
            <Settings className="w-4 h-4" />
            {isTesting ? 'Testing...' : 'Test Connection'}
          </button>

          {connectionStatus === 'success' && (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="w-5 h-5" />
              <span className="text-sm font-medium">Connection successful</span>
            </div>
          )}

          {connectionStatus === 'error' && (
            <div className="flex items-center gap-2 text-red-600">
              <XCircle className="w-5 h-5" />
              <span className="text-sm font-medium">Connection failed</span>
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-gray-200">
          <button
            onClick={handleUploadToS3}
            disabled={isUploading || connectionStatus !== 'success'}
            style={{ backgroundColor: '#2596be' }}
            className="flex items-center gap-2 px-6 py-3 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            onMouseEnter={(e) => {
              if (!e.currentTarget.disabled) {
                e.currentTarget.style.backgroundColor = '#1a7a9a'
              }
            }}
            onMouseLeave={(e) => {
              if (!e.currentTarget.disabled) {
                e.currentTarget.style.backgroundColor = '#2596be'
              }
            }}
          >
            <Upload className="w-4 h-4" />
            {isUploading ? 'Uploading...' : 'Upload to S3'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default S3Config

