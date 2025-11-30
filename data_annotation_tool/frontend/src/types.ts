export interface CSVData {
  filename: string
  headers: string[]
  rows: Record<string, string>[]
  row_count: number
}

export interface S3Config {
  aws_access_key_id: string
  aws_secret_access_key: string
  bucket_name: string
  region_name: string
}

