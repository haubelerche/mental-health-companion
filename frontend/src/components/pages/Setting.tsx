import { Settings, User } from "lucide-react"

const Setting = () => {
  return (
    <div className="relative min-h-screen text-serene-ink border border-white/35 bg-white/40 backdrop-blur-2xl rounded-4xl py-5 px-8">
      <h1 className="font-display text-5xl text-center">Cài đặt</h1>
      {/* Hồ sơ */}
      <div>
        <h2 className="font-display inline-flex items-center gap-3 text-2xl">
          <User className="h-4 w-4" />
          Hồ sơ cá nhân</h2>
      </div>
      {/* Cài đặt chung */}
      <div>
        <h2 className="font-display inline-flex items-center gap-3 text-2xl">
          <Settings className="h-4 w-4" />
          Cài đặt chung</h2>
      </div>
    </div>
  )
}

export default Setting