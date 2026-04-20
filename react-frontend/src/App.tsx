import { ConfigProvider } from 'antd'
import { ChatPage } from './pages/ChatPage'

function App() {
  return (
    <ConfigProvider>
      <ChatPage />
    </ConfigProvider>
  )
}

export default App
