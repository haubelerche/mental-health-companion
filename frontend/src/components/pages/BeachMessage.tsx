import { useEffect, useState } from 'react'
import {
  anonymousShareService,
  type ReplyArchiveItem,
  type SentLetterItem,
} from '../../services/anonymousShareService'
import {
  CinematicBg as BeachCinematicBg,
  LetterOverlay as BeachLetterOverlay,
  ReceivedLetterDialog as BeachReceivedLetterDialog,
  SentLetterDialog as BeachSentLetterDialog,
  WriteOverlay as BeachWriteOverlay,
} from './letter'
import { BeachMessageBeachPanel } from './letter/BeachMessageBeachPanel'
import { BeachMessageCommunityPanel } from './letter/BeachMessageCommunityPanel'
import { BeachMessageTabs } from './letter/BeachMessageTabs'
import { type Letter, type TabId, pickRandomLetter } from './letter/shared'

const FontLink = () => (
  <link
    href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400;1,500&family=Inter:wght@300;400;500&display=swap"
    rel="stylesheet"
  />
)

const ANIMATIONS_CSS = `
  @keyframes fadeUp     { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
  @keyframes fadeIn     { from{opacity:0} to{opacity:1} }
  @keyframes letterOpen { from{opacity:0;transform:translateY(10px) scale(0.98)} to{opacity:1;transform:translateY(0) scale(1)} }
  @keyframes fadeUpCard { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
  @keyframes bottleFloat {
    0%   { transform: translateY(0px)   rotate(-1.5deg); }
    25%  { transform: translateY(-8px)  rotate(1deg); }
    50%  { transform: translateY(-13px) rotate(-1deg); }
    75%  { transform: translateY(-6px)  rotate(1.5deg); }
    100% { transform: translateY(0px)   rotate(-1.5deg); }
  }
  @keyframes rippleExpand {
    0%   { transform: scale(1);   opacity: 0.7; }
    60%  { opacity: 0.3; }
    100% { transform: scale(2.4); opacity: 0; }
  }
  @keyframes bottleShadow {
    0%,100% { transform: scaleX(1);   opacity: 0.22; }
    50%     { transform: scaleX(0.78); opacity: 0.13; }
  }
`

export default function BeachMessage() {
  const [tab, setTab] = useState<TabId>('beach')
  const [pendingLetter, setPendingLetter] = useState<Letter | null>(null)
  const [ripple, setRipple] = useState(false)
  const [openLetter, setOpenLetter] = useState<Letter | null>(null)
  const [showWrite, setShowWrite] = useState(false)
  const [loadingInbox, setLoadingInbox] = useState(false)
  const [loadingSent, setLoadingSent] = useState(false)
  const [sentLetters, setSentLetters] = useState<SentLetterItem[]>([])
  const [replyLetters, setReplyLetters] = useState<ReplyArchiveItem[]>([])
  const [selectedSentLetter, setSelectedSentLetter] = useState<SentLetterItem | null>(null)
  const [selectedReplyLetter, setSelectedReplyLetter] = useState<ReplyArchiveItem | null>(null)
  const [refreshSeed, setRefreshSeed] = useState(0)

  useEffect(() => {
    let active = true
    const loadData = async () => {
      setLoadingInbox(true)
      try {
        const inboxData = await anonymousShareService.getInbox()
        if (active) setPendingLetter((current) => current ?? pickRandomLetter(inboxData.letters))
      } catch {
        if (active) setPendingLetter(null)
      } finally {
        if (active) setLoadingInbox(false)
      }

      setLoadingSent(true)
      try {
        const sentData = await anonymousShareService.getSentLetters()
        if (active) setSentLetters(sentData.letters)
        if (active) setReplyLetters(sentData.reply_letters ?? [])
      } catch {
        if (active) setSentLetters([])
        if (active) setReplyLetters([])
      } finally {
        if (active) setLoadingSent(false)
      }
    }

    void loadData()
    return () => {
      active = false
    }
  }, [refreshSeed])

  const handleBottle = () => {
    if (!pendingLetter) return
    setRipple(true)
    setTimeout(() => {
      setRipple(false)
      setOpenLetter(pendingLetter)
      setPendingLetter(null)
    }, 700)
  }

  const refreshData = () => setRefreshSeed((value) => value + 1)
  const hasBottle = Boolean(pendingLetter)

  return (
    <div className="relative min-h-screen overflow-x-hidden overflow-y-auto">
      <style>{ANIMATIONS_CSS}</style>
      <FontLink />
      <BeachCinematicBg />

      <BeachMessageTabs tab={tab} onChange={setTab} />

      {tab === 'beach' ? (
        <BeachMessageBeachPanel
          loadingInbox={loadingInbox}
          hasBottle={hasBottle}
          ripple={ripple}
          onBottleClick={handleBottle}
          onWrite={() => setShowWrite(true)}
        />
      ) : (
        <BeachMessageCommunityPanel
          loadingSent={loadingSent}
          sentLetters={sentLetters}
          replyLetters={replyLetters}
          onOpenSentLetter={setSelectedSentLetter}
          onOpenReplyLetter={setSelectedReplyLetter}
        />
      )}

      {selectedSentLetter && (
        <BeachSentLetterDialog
          item={selectedSentLetter}
          onClose={() => setSelectedSentLetter(null)}
          onReact={async () => {
            if (!selectedSentLetter.reply) return
            await anonymousShareService.reactToReply(selectedSentLetter.reply.reply_id, 'heart')
            refreshData()
          }}
        />
      )}

      {selectedReplyLetter && (
        <BeachReceivedLetterDialog
          item={selectedReplyLetter}
          onClose={() => setSelectedReplyLetter(null)}
        />
      )}

      {openLetter && (
        <BeachLetterOverlay
          letter={openLetter}
          onClose={() => setOpenLetter(null)}
          onReply={async (content) => {
            await anonymousShareService.reply(openLetter.id, content)
            refreshData()
          }}
          onPass={async () => {
            await anonymousShareService.passItOn(openLetter.id)
            refreshData()
          }}
          onReportSuccess={refreshData}
        />
      )}
      {showWrite && <BeachWriteOverlay onClose={() => setShowWrite(false)} />}
    </div>
  )
}
