import React from 'react'
import LandingHeader from './landing/LandingHeader'
import LandingFooter from './landing/LandingFooter'
import { motion } from 'framer-motion'

const DeleteDataInstructions: React.FC = () => {
    return (
        <div className="min-h-screen bg-serene-bg text-serene-ink">
            <LandingHeader />
            
            <main className="max-w-3xl mx-auto px-6 py-24 pt-32">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <h1 className="text-4xl font-display italic mb-8 text-serene-ink">Hướng dẫn Xóa dữ liệu người dùng</h1>
                    
                    <div className="prose prose-slate max-w-none">
                        <p className="text-lg text-serene-muted mb-8 leading-relaxed">
                            Tại Serene, chúng tôi tôn trọng quyền riêng tư và quyền kiểm soát dữ liệu cá nhân của bạn. 
                            Nếu bạn không còn muốn sử dụng dịch vụ và muốn xóa toàn bộ dữ liệu của mình, vui lòng làm theo hướng dẫn dưới đây.
                        </p>

                        <section className="mb-10">
                            <h2 className="text-2xl font-semibold mb-4 text-serene-primary">Cách 1: Xóa trong ứng dụng</h2>
                            <p className="mb-4">Bạn có thể xóa tài khoản trực tiếp trong phần cài đặt:</p>
                            <ol className="list-decimal pl-6 space-y-2">
                                <li>Đăng nhập vào tài khoản Serene của bạn.</li>
                                <li>Truy cập vào mục <strong>Hồ sơ</strong> hoặc <strong>Cài đặt</strong>.</li>
                                <li>Tìm phần <strong>Quản lý tài khoản</strong>.</li>
                                <li>Chọn <strong>Xóa tài khoản</strong> và xác nhận yêu cầu.</li>
                            </ol>
                            <p className="mt-4 text-sm italic text-red-500">Lưu ý: Hành động này không thể hoàn tác. Toàn bộ tin nhắn, dữ liệu sức khỏe và lịch sử sẽ bị xóa vĩnh viễn.</p>
                        </section>

                        <section className="mb-10">
                            <h2 className="text-2xl font-semibold mb-4 text-serene-primary">Cách 2: Gửi yêu cầu qua Email</h2>
                            <p className="mb-4">
                                Nếu bạn không thể truy cập tài khoản, vui lòng gửi email yêu cầu xóa dữ liệu đến bộ phận hỗ trợ của chúng tôi:
                            </p>
                            <div className="bg-serene-surface p-6 rounded-2xl border border-serene-border">
                                <p className="mb-2"><strong>Địa chỉ email:</strong> <a href="mailto:support@serene.com" className="text-serene-primary font-medium">support@serene.com</a></p>
                                <p className="mb-2"><strong>Tiêu đề:</strong> Yêu cầu xóa dữ liệu - [Tên của bạn hoặc Email đăng ký]</p>
                                <p><strong>Nội dung:</strong> Vui lòng cung cấp email đã dùng để đăng ký tài khoản Serene để chúng tôi có thể xác minh và xử lý yêu cầu của bạn.</p>
                            </div>
                        </section>

                        <section className="mb-10">
                            <h2 className="text-2xl font-semibold mb-4 text-serene-primary">Thời gian xử lý</h2>
                            <p className="leading-relaxed">
                                Sau khi nhận được yêu cầu hợp lệ, chúng tôi sẽ tiến hành xóa dữ liệu của bạn khỏi hệ thống trong vòng <strong>7 ngày làm việc</strong>. 
                                Bạn sẽ nhận được email xác nhận sau khi quá trình xóa hoàn tất.
                            </p>
                        </section>
                    </div>
                </motion.div>
            </main>

            <LandingFooter />
        </div>
    )
}

export default DeleteDataInstructions
