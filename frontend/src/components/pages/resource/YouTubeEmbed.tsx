import { X } from 'lucide-react'
import Modal from 'react-modal'

export function getYouTubeVideoId(url: string): string | null {
    if (!url) return null

    // Handle youtube.com/watch?v=ID format
    let match = url.match(/(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/)
    if (match) return match[1]

    // Handle youtu.be/ID format
    match = url.match(/(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})/)
    if (match) return match[1]

    // Handle youtube.com/embed/ID format
    match = url.match(/(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/)
    if (match) return match[1]

    return null
}

export function isYouTubeUrl(url: string): boolean {
    return getYouTubeVideoId(url) !== null
}

interface YouTubeEmbedProps {
    url: string
    title: string
    isOpen: boolean
    onClose: () => void
}

export function YouTubeEmbed({ url, title, isOpen, onClose }: YouTubeEmbedProps) {
    const videoId = getYouTubeVideoId(url)

    if (!videoId) return null

    return (
        <Modal
            isOpen={isOpen}
            onRequestClose={onClose}
            contentLabel={title}
            overlayClassName="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            className="relative w-full max-w-4xl outline-none"
            bodyOpenClassName="overflow-hidden"
        >
            <div className="rounded-lg bg-black shadow-2xl">
                {/* Close button */}
                <button
                    type="button"
                    onClick={onClose}
                    className="absolute -top-12 right-0 rounded-full p-2 text-white transition hover:bg-white/10 z-10"
                    aria-label="Close"
                >
                    <X className="h-6 w-6" />
                </button>

                {/* Video container */}
                <div className="relative w-full bg-black rounded-t-lg overflow-hidden">
                    <div className="aspect-video">
                        <iframe
                            src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
                            title={title}
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                            className="h-full w-full"
                        />
                    </div>
                </div>

                {/* Title */}
                <div className="rounded-b-lg bg-white/5 p-4 text-white">
                    <p className="font-display text-lg">{title}</p>
                </div>
            </div>
        </Modal>
    )
}
