import { FileText } from 'lucide-react'

const Header = () => {
  const primaryColor = '#2596be'
  return (
    <header 
      className="sticky top-0 z-50 backdrop-blur-xl"
      style={{ 
        background: 'rgba(255, 255, 255, 0.8)',
        borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
      }}
    >
      <div className="container mx-auto px-6 py-5 max-w-7xl">
        <div className="flex items-center gap-4">
          <div 
            className="p-2.5 rounded-xl transition-all duration-300"
            style={{ 
              background: `linear-gradient(135deg, ${primaryColor}15 0%, ${primaryColor}08 100%)`,
              border: `1px solid ${primaryColor}20`
            }}
          >
            <FileText className="w-5 h-5" style={{ color: primaryColor }} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight" style={{ color: '#1d1d1f' }}>
              Data Annotation Tool
            </h1>
            <p className="text-sm mt-0.5" style={{ color: '#86868b' }}>
              Upload, edit, and manage CSV files
            </p>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header

