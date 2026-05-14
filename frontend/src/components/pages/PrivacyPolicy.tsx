import React from 'react'
import LandingHeader from './landing/LandingHeader'
import LandingFooter from './landing/LandingFooter'
import { motion } from 'framer-motion'

const PrivacyPolicy: React.FC = () => {
    return (
        <div className="min-h-screen bg-serene-bg text-serene-ink">
            <LandingHeader />
            
            <main className="max-w-4xl mx-auto px-6 py-24 pt-32">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <h1 className="text-4xl md:text-5xl font-display italic mb-8 text-serene-ink">Chính sách Bảo mật & Điều khoản Dịch vụ</h1>
                    <p className="text-lg text-serene-muted mb-12">Cập nhật lần cuối: 14 tháng 5, 2026</p>

                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold mb-4 text-serene-primary">1. Thu thập thông tin</h2>
                        <p className="mb-4 leading-relaxed">
                            Chúng tôi thu thập thông tin để cung cấp dịch vụ tốt hơn cho tất cả người dùng. Các loại thông tin chúng tôi thu thập bao gồm:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mb-4">
                            <li>Thông tin cá nhân (Tên, email, số điện thoại) khi bạn đăng ký tài khoản.</li>
                            <li>Dữ liệu sử dụng (Cách bạn tương tác với ứng dụng, thời gian truy cập).</li>
                            <li>Thông tin thiết bị (Loại máy, hệ điều hành).</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold mb-4 text-serene-primary">2. Sử dụng thông tin</h2>
                        <p className="mb-4 leading-relaxed">
                            Thông tin của bạn được sử dụng để:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mb-4">
                            <li>Cung cấp, duy trì và cải thiện các tính năng của Serene.</li>
                            <li>Cá nhân hóa trải nghiệm người dùng.</li>
                            <li>Gửi thông báo quan trọng về tài khoản và dịch vụ.</li>
                            <li>Đảm bảo an ninh và ngăn chặn các hành vi gian lận.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold mb-4 text-serene-primary">3. Bảo mật dữ liệu</h2>
                        <p className="mb-4 leading-relaxed">
                            Chúng tôi cam kết bảo vệ dữ liệu của bạn bằng các biện pháp kỹ thuật và tổ chức nghiêm ngặt. Dữ liệu của bạn được mã hóa trong quá trình truyền tải và lưu trữ.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold mb-4 text-serene-primary">4. Điều khoản dịch vụ</h2>
                        <p className="mb-4 leading-relaxed">
                            Bằng cách sử dụng Serene, bạn đồng ý tuân thủ các quy định sau:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mb-4">
                            <li>Bạn phải từ 13 tuổi trở lên để sử dụng dịch vụ.</li>
                            <li>Bạn chịu trách nhiệm bảo mật mật khẩu tài khoản của mình.</li>
                            <li>Không sử dụng dịch vụ cho bất kỳ mục đích trái pháp luật nào.</li>
                            <li>Chúng tôi có quyền tạm ngừng hoặc chấm dứt tài khoản nếu phát hiện vi phạm.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold mb-4 text-serene-primary">5. Liên hệ</h2>
                        <p className="mb-4 leading-relaxed">
                            Nếu bạn có bất kỳ câu hỏi nào về Chính sách Bảo mật này, vui lòng liên hệ với chúng tôi qua email: <span className="font-medium text-serene-primary">support@serene.com</span>
                        </p>
                    </section>
                </motion.div>
            </main>

            <LandingFooter />
        </div>
    )
}

export default PrivacyPolicy
