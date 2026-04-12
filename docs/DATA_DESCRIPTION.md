# BÁO CÁO KIẾN TRÚC DỮ LIỆU - MULTI-AGENT THERAPIST

## Thông tin dự án
- **Tên cụ thể**: Multi-Agent Therapist Sàng Lọc và Hỗ Trợ Sức Khỏe Tinh Thần
- **Stack**: React.js + FastAPI + LangGraph + PostgreSQL + pgvector
- **Ngày**: 2026-04-12
- **Phiên bản**: 1.0

---

## MỤC LỤC

1. [Tổng quan kiến trúc dữ liệu](#1-tổng-quan-kiến-trúc-dữ-liệu)
2. [Luồng dữ liệu đầu vào (Input Data Flow)](#2-luồng-dữ-liệu-đầu-vào)
3. [Luồng dữ liệu đầu ra (Output Data Flow)](#3-luồng-dữ-liệu-đầu-ra)
4. [JSON Schema chuẩn hóa](#4-json-schema-chuẩn-hóa)
5. [Cấu trúc Database Schema](#5-cấu-trúc-database-schema)
6. [Quy trình vận hành dữ liệu](#6-quy-trình-vận-hành-dữ-liệu)
7. [Tối ưu hóa vòng lặp dữ liệu (Data Flywheel)](#7-tối-ưu-hóa-vòng-lặp-dữ-liệu)
8. [Security & Privacy](#8-security--privacy)
9. [Monitoring & Analytics](#9-monitoring--analytics)

---

## 1. TỔNG QUAN KIẾN TRÚC DỮ LIỆU

### 1.1. Sơ đồ tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React.js)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Chat UI      │  │ State Mgmt   │  │ WebSocket    │          │
│  │ Components   │  │ (Zustand)    │  │ Client       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │ (HTTPS + WebSocket)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY                                 │
│                      (FastAPI)                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ CORS/Auth    │  │ Rate Limiter │  │ Input Valid. │          │
│  │ JWT Tokens   │  │ Redis Cache  │  │ Pydantic     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                            │
│                      (LangGraph)                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  State Machine: Input → Process → Memory → Output        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─┬───────────────┬───────────────┬───────────────┬──────────────┘
  │               │               │               │
  ▼               ▼               ▼               ▼
┌─────────┐  ┌─────────┐  ┌──────────┐  ┌─────────────┐
│ LLM     │  │ Guard   │  │ Memory   │  │ PostgreSQL  │
│ Service │  │ rails   │  │ Retrieval│  │ + pgvector  │
│ (OpenAI)│  │ (NeMo)  │  │ (RAG)    │  │             │
└─────────┘  └─────────┘  └──────────┘  └─────────────┘
```

### 1.2. Các loại dữ liệu chính

| Loại dữ liệu | Nguồn | Mục đích | Lưu trữ |
|-------------|-------|----------|---------|
| **User Input** | React.js UI | Câu hỏi/yêu cầu từ user | Transient + PostgreSQL |
| **Conversation History** | LangGraph state | Context cho LLM | PostgreSQL |
| **User Profile** | Registration/Settings | Personalization | PostgreSQL (encrypted) |
| **Semantic Memory** | Conversation → Embedding | Long-term memory | pgvector |
| **System Logs** | All components | Debugging/Analytics | PostgreSQL + File logs |
| **Feedback Data** | User ratings | Model improvement | PostgreSQL |
| **Generated Responses** | LLM output | Display to user | Transient + PostgreSQL |

---


## 2. LUỒNG DỮ LIỆU ĐẦU VÀO

### 2.1. Input Data Sources

#### **A. User Message Input**

```
React UI → WebSocket/REST API → FastAPI → LangGraph State
```

**Cấu trúc JSON đầu vào từ React:**

```json
{
  "message_id": "uuid-v4",
  "user_id": "user_12345",
  "session_id": "session_67890",
  "content": {
    "text": "Hôm nay tôi cảm thấy hơi buồn về công việc",
    "attachments": [],
    "metadata": {
      "timestamp": "2026-04-12T14:30:00Z",
      "client_type": "web",
      "language": "vi"
    }
  },
  "context": {
    "previous_messages": 5,
    "emotion_state": "neutral",
    "topic_continuity": true
  }
}
```

#### **B. User Profile Data**

```json
{
  "user_id": "user_12345",
  "profile": {
    "display_name": "Nguyễn Văn A",
    "preferences": {
      "communication_style": "friendly",
      "topics_of_interest": ["công nghệ", "du lịch", "sức khỏe"],
      "language": "vi",
      "timezone": "Asia/Ho_Chi_Minh"
    },
    "privacy": {
      "data_retention_days": 90,
      "analytics_opt_in": true,
      "pii_encryption": true
    }
  },
  "created_at": "2026-01-15T08:00:00Z",
  "last_active": "2026-04-12T14:25:00Z"
}
```

#### **C. System Context Input**

```json
{
  "request_id": "req_abc123",
  "environment": "production",
  "guardrails_config": {
    "enabled": true,
    "policy": "default",
    "sensitivity_level": "high"
  },
  "llm_config": {
    "model": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": true
  }
}
```

### 2.2. Input Validation Pipeline

```python
# Pseudo-code minh họa
class InputValidationPipeline:
    def validate(self, raw_input: dict) -> ValidatedInput:
        # Step 1: Schema validation
        validated = self.validate_schema(raw_input)
        
        # Step 2: Security check
        validated = self.sanitize_input(validated)
        
        # Step 3: NeMo Guardrails check
        validated = self.check_guardrails(validated)
        
        # Step 4: Rate limit check
        self.check_rate_limit(validated.user_id)
        
        return validated
```

**Validation Rules:**

| Field | Rule | Error Response |
|-------|------|----------------|
| `user_id` | UUID format, exists in DB | 401 Unauthorized |
| `content.text` | Max 4000 chars, no malicious code | 400 Bad Request |
| `session_id` | Valid session, not expired | 403 Forbidden |
| Rate limit | Max 60 req/min per user | 429 Too Many Requests |

---

## 3. LUỒNG DỮ LIỆU ĐẦU RA

### 3.1. Output Data Structure

#### **A. AI Response Output**

```json
{
  "response_id": "resp_xyz789",
  "message_id": "msg_abc123",
  "user_id": "user_12345",
  "session_id": "session_67890",
  "content": {
    "text": "Tôi hiểu cảm giác của bạn. Công việc đôi khi có thể gây áp lực. Bạn muốn chia sẻ thêm về điều gì đang làm bạn buồn không?",
    "emotion_detected": "empathetic",
    "suggested_actions": [
      {
        "type": "breathing_exercise",
        "title": "Thử bài tập thở 4-7-8",
        "url": "/wellness/breathing"
      }
    ]
  },
  "metadata": {
    "generated_at": "2026-04-12T14:30:02Z",
    "latency_ms": 1847,
    "model_used": "gpt-4o",
    "tokens": {
      "prompt": 345,
      "completion": 67,
      "total": 412
    },
    "guardrails_passed": true
  },
  "memory_updated": {
    "new_facts_stored": 1,
    "context_retrieved": 3
  }
}
```

#### **B. Memory Storage Output**

Sau mỗi conversation, hệ thống tự động extract và lưu:

```json
{
  "memory_id": "mem_456def",
  "user_id": "user_12345",
  "session_id": "session_67890",
  "extracted_info": {
    "facts": [
      {
        "type": "emotion",
        "content": "Người dùng đang cảm thấy buồn về công việc",
        "confidence": 0.89,
        "timestamp": "2026-04-12T14:30:00Z"
      },
      {
        "type": "topic",
        "content": "Đang quan tâm đến sức khỏe tinh thần",
        "confidence": 0.76,
        "timestamp": "2026-04-12T14:30:00Z"
      }
    ],
    "embedding": [0.123, -0.456, 0.789, ...], // 1536 dims
    "metadata": {
      "importance_score": 0.82,
      "emotion_tag": "stress",
      "should_recall": true
    }
  }
}
```

#### **C. Analytics Output**

```json
{
  "analytics_event": {
    "event_id": "evt_analytics_001",
    "event_type": "conversation_completed",
    "user_id": "user_12345_hashed",  // Privacy-safe
    "timestamp": "2026-04-12T14:30:05Z",
    "metrics": {
      "conversation_length": 7,
      "avg_response_time_ms": 1623,
      "user_satisfaction": null,  // Chờ feedback
      "topics_discussed": ["work", "mental_health"],
      "guardrails_triggered": 0,
      "memory_retrievals": 3
    },
    "system_metrics": {
      "llm_cost_usd": 0.0082,
      "cache_hit_rate": 0.67,
      "error_count": 0
    }
  }
}
```

### 3.2. Output Delivery Channels

```
┌─────────────────────┐
│  LangGraph Output   │
└──────────┬──────────┘
           │
           ├─────────────► Streamlit UI (real-time)
           │
           ├─────────────► PostgreSQL (persistent)
           │
           ├─────────────► pgvector (embeddings)
           │
           └─────────────► Logging system
```

---

## 4. JSON SCHEMA CHUẨN HÓA

### 4.1. Core Schemas

#### **UserMessage Schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["message_id", "user_id", "session_id", "content"],
  "properties": {
    "message_id": {
      "type": "string",
      "pattern": "^msg_[a-zA-Z0-9]{12}$",
      "description": "Unique message identifier"
    },
    "user_id": {
      "type": "string",
      "pattern": "^user_[a-zA-Z0-9]{10}$",
      "description": "User identifier"
    },
    "session_id": {
      "type": "string",
      "pattern": "^session_[a-zA-Z0-9]{12}$",
      "description": "Conversation session ID"
    },
    "content": {
      "type": "object",
      "required": ["text"],
      "properties": {
        "text": {
          "type": "string",
          "minLength": 1,
          "maxLength": 4000,
          "description": "Message content"
        },
        "attachments": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "type": {"enum": ["image", "document", "audio"]},
              "url": {"type": "string", "format": "uri"},
              "size_bytes": {"type": "integer", "minimum": 0}
            }
          }
        },
        "metadata": {
          "type": "object",
          "properties": {
            "timestamp": {"type": "string", "format": "date-time"},
            "client_type": {"enum": ["web", "mobile", "api"]},
            "language": {"type": "string", "pattern": "^[a-z]{2}$"}
          }
        }
      }
    }
  }
}
```

#### **AIResponse Schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["response_id", "message_id", "content"],
  "properties": {
    "response_id": {
      "type": "string",
      "pattern": "^resp_[a-zA-Z0-9]{12}$"
    },
    "message_id": {
      "type": "string",
      "pattern": "^msg_[a-zA-Z0-9]{12}$"
    },
    "content": {
      "type": "object",
      "required": ["text"],
      "properties": {
        "text": {
          "type": "string",
          "minLength": 1,
          "maxLength": 8000
        },
        "emotion_detected": {
          "enum": ["neutral", "happy", "sad", "angry", "empathetic", "curious"]
        },
        "suggested_actions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "type": {"type": "string"},
              "title": {"type": "string"},
              "url": {"type": "string", "format": "uri"}
            }
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "generated_at": {"type": "string", "format": "date-time"},
        "latency_ms": {"type": "integer", "minimum": 0},
        "model_used": {"enum": ["gpt-4o", "gpt-4o-mini"]},
        "tokens": {
          "type": "object",
          "properties": {
            "prompt": {"type": "integer"},
            "completion": {"type": "integer"},
            "total": {"type": "integer"}
          }
        }
      }
    }
  }
}
```

#### **Memory Schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["memory_id", "user_id", "extracted_info"],
  "properties": {
    "memory_id": {
      "type": "string",
      "pattern": "^mem_[a-zA-Z0-9]{12}$"
    },
    "user_id": {
      "type": "string",
      "pattern": "^user_[a-zA-Z0-9]{10}$"
    },
    "extracted_info": {
      "type": "object",
      "required": ["facts", "embedding"],
      "properties": {
        "facts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["type", "content", "confidence"],
            "properties": {
              "type": {
                "enum": ["emotion", "preference", "fact", "topic", "goal"]
              },
              "content": {"type": "string"},
              "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
              },
              "timestamp": {"type": "string", "format": "date-time"}
            }
          }
        },
        "embedding": {
          "type": "array",
          "items": {"type": "number"},
          "minItems": 1536,
          "maxItems": 1536,
          "description": "OpenAI text-embedding-3-small output"
        },
        "metadata": {
          "type": "object",
          "properties": {
            "importance_score": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "emotion_tag": {"type": "string"},
            "should_recall": {"type": "boolean"}
          }
        }
      }
    }
  }
}
```

### 4.2. Validation Implementation

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime
import re

class UserMessageContent(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    attachments: Optional[List[dict]] = []
    metadata: Optional[dict] = {}

class UserMessage(BaseModel):
    message_id: str = Field(..., regex=r"^msg_[a-zA-Z0-9]{12}$")
    user_id: str = Field(..., regex=r"^user_[a-zA-Z0-9]{10}$")
    session_id: str = Field(..., regex=r"^session_[a-zA-Z0-9]{12}$")
    content: UserMessageContent
    
    @validator('content')
    def validate_content(cls, v):
        # XSS prevention
        if re.search(r'<script|javascript:|onerror=', v.text, re.I):
            raise ValueError("Potentially malicious content detected")
        return v

class AIResponseMetadata(BaseModel):
    generated_at: datetime
    latency_ms: int = Field(..., ge=0)
    model_used: Literal["gpt-4o", "gpt-4o-mini"]
    tokens: dict

class AIResponse(BaseModel):
    response_id: str = Field(..., regex=r"^resp_[a-zA-Z0-9]{12}$")
    message_id: str
    content: dict
    metadata: AIResponseMetadata
```

---

## 5. CẤU TRÚC DATABASE SCHEMA

### 5.1. PostgreSQL Tables

#### **Table: users**

```sql
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile data (encrypted with Fernet)
    profile_data_encrypted BYTEA,
    
    -- Preferences
    preferences JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Privacy settings
    data_retention_days INTEGER DEFAULT 90,
    analytics_opt_in BOOLEAN DEFAULT FALSE,
    
    -- Indexes
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_active ON users(last_active);
```

#### **Table: conversations**

```sql
CREATE TABLE conversations (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Conversation metadata
    title VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
    
    -- Timestamps
    started_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    
    -- Statistics
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Indexes
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_conv_user_id ON conversations(user_id);
CREATE INDEX idx_conv_last_message ON conversations(last_message_at DESC);
CREATE INDEX idx_conv_status ON conversations(status) WHERE status = 'active';
```

#### **Table: messages**

```sql
CREATE TABLE messages (
    message_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Message data
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    
    -- Metadata
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- LLM metadata (for assistant messages)
    model_used VARCHAR(50),
    tokens_prompt INTEGER,
    tokens_completion INTEGER,
    latency_ms INTEGER,
    
    -- Indexes
    CONSTRAINT fk_session FOREIGN KEY (session_id) REFERENCES conversations(session_id),
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant'))
);

CREATE INDEX idx_msg_session ON messages(session_id, timestamp);
CREATE INDEX idx_msg_user ON messages(user_id, timestamp);
CREATE INDEX idx_msg_timestamp ON messages(timestamp DESC);

-- Full-text search index for BM25
CREATE INDEX idx_msg_fts ON messages 
USING gin(to_tsvector('english', content))
WHERE role = 'user';
```

#### **Table: conversation_memories (pgvector)**

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE conversation_memories (
    memory_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    session_id VARCHAR(50) REFERENCES conversations(session_id) ON DELETE SET NULL,
    
    -- Memory content
    content TEXT NOT NULL,
    memory_type VARCHAR(50),  -- 'emotion', 'preference', 'fact', 'topic', 'goal'
    
    -- Embedding for semantic search
    embedding vector(1536) NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    importance_score FLOAT CHECK (importance_score >= 0 AND importance_score <= 1),
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Access tracking
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Critical: Separate index per user for isolation
CREATE INDEX idx_mem_user_embedding ON conversation_memories 
USING hnsw (embedding vector_cosine_ops)
WHERE is_deleted = FALSE;

CREATE INDEX idx_mem_user_id ON conversation_memories(user_id, created_at DESC);
CREATE INDEX idx_mem_type ON conversation_memories(user_id, memory_type);
CREATE INDEX idx_mem_importance ON conversation_memories(user_id, importance_score DESC);

-- Row-Level Security to prevent data leakage
ALTER TABLE conversation_memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_memory_isolation ON conversation_memories
    USING (user_id = current_setting('app.current_user_id', TRUE)::text);
```

#### **Table: feedback**

```sql
CREATE TABLE feedback (
    feedback_id VARCHAR(50) PRIMARY KEY,
    message_id VARCHAR(50) NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Feedback data
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_type VARCHAR(50),  -- 'helpful', 'not_helpful', 'offensive', 'incorrect'
    comment TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_feedback_message ON feedback(message_id);
CREATE INDEX idx_feedback_user ON feedback(user_id, created_at DESC);
CREATE INDEX idx_feedback_rating ON feedback(rating);
```

#### **Table: system_logs**

```sql
CREATE TABLE system_logs (
    log_id BIGSERIAL PRIMARY KEY,
    
    -- Request tracking
    request_id VARCHAR(100),
    user_id VARCHAR(50),
    
    -- Log data
    level VARCHAR(20) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    component VARCHAR(100),  -- 'api', 'langgraph', 'llm', 'guardrails', etc.
    message TEXT NOT NULL,
    
    -- Error details
    error_code VARCHAR(50),
    stack_trace TEXT,
    
    -- Performance metrics
    duration_ms INTEGER,
    
    -- Metadata
    timestamp TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX idx_logs_level ON system_logs(level) WHERE level IN ('ERROR', 'CRITICAL');
CREATE INDEX idx_logs_user ON system_logs(user_id, timestamp DESC);
CREATE INDEX idx_logs_request ON system_logs(request_id);

-- Partition by month for performance
CREATE TABLE system_logs_2026_04 PARTITION OF system_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

### 5.2. Data Encryption

```sql
-- Encryption functions (using pgcrypto)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Function to encrypt PII data
CREATE OR REPLACE FUNCTION encrypt_pii(data TEXT, key TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, key);
END;
$$ LANGUAGE plpgsql;

-- Function to decrypt PII data
CREATE OR REPLACE FUNCTION decrypt_pii(encrypted_data BYTEA, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted_data, key);
END;
$$ LANGUAGE plpgsql;
```

---

## 6. QUY TRÌNH VẬN HÀNH DỮ LIỆU

### 6.1. Data Lifecycle Management

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA LIFECYCLE STAGES                         │
└─────────────────────────────────────────────────────────────────┘

1. CREATION (Input → Validation → Storage)
   ├─ User sends message
   ├─ FastAPI validates schema
   ├─ LangGraph processes
   └─ PostgreSQL stores

2. PROCESSING (Retrieval → Enhancement → Generation)
   ├─ Retrieve user context from pgvector
   ├─ Apply LangGraph orchestration
   ├─ LLM generates response
   └─ Guardrails check output

3. STORAGE (Persistence → Embedding → Indexing)
   ├─ Save message to PostgreSQL
   ├─ Generate embedding
   ├─ Store in pgvector
   └─ Update indexes

4. RETENTION (Active → Archived → Deleted)
   ├─ Active: 0-90 days (hot storage)
   ├─ Archived: 91-365 days (cold storage)
   └─ Deleted: >365 days (GDPR compliance)

5. ANALYTICS (Aggregate → Anonymize → Report)
   ├─ Daily aggregation
   ├─ Remove PII
   └─ Generate insights
```

### 6.2. Data Flow Pipeline

#### **Pipeline 1: User Message → AI Response**

```python
# Workflow implementation (pseudo-code)

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class ConversationState(TypedDict):
    # Input
    user_id: str
    session_id: str
    message: str
    
    # Processing
    validated: bool
    guardrails_passed: bool
    retrieved_context: list
    
    # Output
    response: str
    memory_updates: list
    metadata: dict

def create_conversation_graph():
    workflow = StateGraph(ConversationState)
    
    # Define nodes
    workflow.add_node("validate_input", validate_input_node)
    workflow.add_node("check_guardrails", check_guardrails_node)
    workflow.add_node("retrieve_memory", retrieve_memory_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("update_memory", update_memory_node)
    workflow.add_node("save_conversation", save_conversation_node)
    
    # Define edges
    workflow.set_entry_point("validate_input")
    
    workflow.add_edge("validate_input", "check_guardrails")
    workflow.add_conditional_edges(
        "check_guardrails",
        lambda x: x["guardrails_passed"],
        {
            True: "retrieve_memory",
            False: END
        }
    )
    workflow.add_edge("retrieve_memory", "generate_response")
    workflow.add_edge("generate_response", "update_memory")
    workflow.add_edge("update_memory", "save_conversation")
    workflow.add_edge("save_conversation", END)
    
    return workflow.compile()

# Node implementations

async def validate_input_node(state: ConversationState):
    """Validate and sanitize user input"""
    # 1. Schema validation
    validated_message = UserMessage.parse_obj({
        "message_id": generate_id("msg"),
        "user_id": state["user_id"],
        "session_id": state["session_id"],
        "content": {"text": state["message"]}
    })
    
    # 2. Security checks
    if contains_injection_attempt(validated_message.content.text):
        raise SecurityError("Malicious input detected")
    
    state["validated"] = True
    return state

async def check_guardrails_node(state: ConversationState):
    """Check input against NeMo Guardrails"""
    from nemoguardrails import RailsConfig, LLMRails
    
    config = RailsConfig.from_path("./config/guardrails")
    rails = LLMRails(config)
    
    # Check input
    result = await rails.generate_async(
        messages=[{"role": "user", "content": state["message"]}]
    )
    
    state["guardrails_passed"] = not result.get("blocked", False)
    return state

async def retrieve_memory_node(state: ConversationState):
    """Retrieve relevant context from pgvector"""
    from langchain_community.vectorstores import PGVector
    from langchain_openai import OpenAIEmbeddings
    
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    vector_store = PGVector(
        connection_string=DATABASE_URL,
        embedding_function=embeddings,
        collection_name="conversation_memories"
    )
    
    # CRITICAL: Filter by user_id to prevent data leakage
    retrieved = vector_store.similarity_search(
        state["message"],
        k=5,
        filter={
            "user_id": state["user_id"],
            "is_deleted": False
        }
    )
    
    state["retrieved_context"] = [doc.page_content for doc in retrieved]
    return state

async def generate_response_node(state: ConversationState):
    """Generate AI response using LLM"""
    from openai import AsyncOpenAI
    
    client = AsyncOpenAI()
    
    # Build prompt with context
    system_prompt = f"""You are a helpful AI assistant.
    
User context:
{chr(10).join(state["retrieved_context"])}

Respond in a friendly, empathetic manner."""
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["message"]}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    state["response"] = response.choices[0].message.content
    state["metadata"] = {
        "model": "gpt-4o",
        "tokens": {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens
        }
    }
    
    return state

async def update_memory_node(state: ConversationState):
    """Extract and store new memories"""
    # 1. Extract facts from conversation
    facts = await extract_facts(
        user_message=state["message"],
        ai_response=state["response"]
    )
    
    # 2. Generate embeddings
    embeddings_client = OpenAIEmbeddings(model="text-embedding-3-small")
    
    memories = []
    for fact in facts:
        embedding = await embeddings_client.aembed_query(fact["content"])
        
        memories.append({
            "memory_id": generate_id("mem"),
            "user_id": state["user_id"],
            "session_id": state["session_id"],
            "content": fact["content"],
            "memory_type": fact["type"],
            "embedding": embedding,
            "confidence": fact["confidence"],
            "importance_score": calculate_importance(fact)
        })
    
    state["memory_updates"] = memories
    return state

async def save_conversation_node(state: ConversationState):
    """Persist conversation to database"""
    async with database.transaction():
        # 1. Save user message
        await db.execute("""
            INSERT INTO messages (message_id, session_id, user_id, role, content, timestamp)
            VALUES ($1, $2, $3, 'user', $4, NOW())
        """, generate_id("msg"), state["session_id"], state["user_id"], state["message"])
        
        # 2. Save AI response
        await db.execute("""
            INSERT INTO messages (message_id, session_id, user_id, role, content, 
                                  model_used, tokens_prompt, tokens_completion, timestamp)
            VALUES ($1, $2, $3, 'assistant', $4, $5, $6, $7, NOW())
        """, 
            generate_id("msg"), 
            state["session_id"], 
            state["user_id"], 
            state["response"],
            state["metadata"]["model"],
            state["metadata"]["tokens"]["prompt"],
            state["metadata"]["tokens"]["completion"]
        )
        
        # 3. Save memories to pgvector
        for mem in state["memory_updates"]:
            await db.execute("""
                INSERT INTO conversation_memories 
                (memory_id, user_id, session_id, content, memory_type, 
                 embedding, confidence, importance_score, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            """, 
                mem["memory_id"],
                mem["user_id"],
                mem["session_id"],
                mem["content"],
                mem["memory_type"],
                mem["embedding"],
                mem["confidence"],
                mem["importance_score"]
            )
        
        # 4. Update conversation metadata
        await db.execute("""
            UPDATE conversations 
            SET last_message_at = NOW(),
                message_count = message_count + 2,
                total_tokens = total_tokens + $1
            WHERE session_id = $2
        """, state["metadata"]["tokens"]["total"], state["session_id"])
    
    return state
```

### 6.3. FastAPI WebSocket Endpoint

```python
# Backend WebSocket handler for real-time communication

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import asyncio
import json

app = FastAPI()

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
    
    async def stream_message(self, user_id: str, message_generator):
        """Stream LLM response chunks to client"""
        if user_id not in self.active_connections:
            return
        
        websocket = self.active_connections[user_id]
        
        async for chunk in message_generator:
            await websocket.send_json({
                "type": "message_chunk",
                "content": chunk
            })

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str = None  # Get from query params or headers
):
    # Authenticate user
    if not await verify_token(token, user_id):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            # Receive message from React frontend
            data = await websocket.receive_json()
            
            if data.get("type") == "send_message":
                await handle_message(user_id, data, websocket)
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f"User {user_id} disconnected")
    
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)
        await websocket.close(code=1011, reason="Internal error")

async def handle_message(user_id: str, data: dict, websocket: WebSocket):
    """Process message and stream response"""
    
    try:
        # Validate input
        message_request = SendMessageRequest(**data)
        
        # Build LangGraph state
        initial_state = {
            "user_id": user_id,
            "session_id": message_request.session_id,
            "message": message_request.content.text,
            "validated": False,
            "guardrails_passed": False,
            "retrieved_context": [],
            "response": "",
            "memory_updates": [],
            "metadata": {}
        }
        
        # Run LangGraph workflow
        workflow = create_conversation_graph()
        
        # Stream response chunks
        async for state in workflow.astream(initial_state):
            # If response is being generated, stream it
            if "response" in state and state["response"]:
                await manager.send_message(user_id, {
                    "type": "message_chunk",
                    "content": state["response"]
                })
        
        # Send final complete message
        final_message = {
            "type": "message_complete",
            "message": {
                "message_id": generate_id("msg"),
                "role": "assistant",
                "content": state["response"],
                "timestamp": datetime.now().isoformat(),
                "metadata": state["metadata"]
            }
        }
        
        await manager.send_message(user_id, final_message)
    
    except Exception as e:
        await manager.send_message(user_id, {
            "type": "message_error",
            "error": str(e)
        })

# REST endpoints for React app
@app.post("/api/messages")
async def send_message_rest(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Fallback REST endpoint if WebSocket unavailable"""
    
    initial_state = {
        "user_id": current_user.user_id,
        "session_id": request.session_id,
        "message": request.content.text
    }
    
    workflow = create_conversation_graph()
    final_state = await workflow.ainvoke(initial_state)
    
    return {
        "message": {
            "message_id": generate_id("msg"),
            "role": "assistant",
            "content": final_state["response"],
            "timestamp": datetime.now().isoformat(),
            "metadata": final_state["metadata"]
        }
    }

@app.get("/api/conversations")
async def get_conversations(
    current_user: User = Depends(get_current_user)
):
    """Get user's conversation list"""
    
    conversations = await db.fetch("""
        SELECT 
            session_id,
            title,
            status,
            started_at,
            last_message_at,
            message_count
        FROM conversations
        WHERE user_id = $1
          AND status != 'deleted'
        ORDER BY last_message_at DESC
        LIMIT 50
    """, current_user.user_id)
    
    return {"conversations": conversations}

@app.get("/api/conversations/{session_id}/messages")
async def get_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    before: str = None  # Message ID for pagination
):
    """Get conversation message history"""
    
    query = """
        SELECT 
            message_id,
            role,
            content,
            timestamp,
            metadata
        FROM messages
        WHERE session_id = $1
          AND user_id = $2
    """
    
    params = [session_id, current_user.user_id]
    
    if before:
        query += " AND timestamp < (SELECT timestamp FROM messages WHERE message_id = $3)"
        params.append(before)
    
    query += " ORDER BY timestamp DESC LIMIT $" + str(len(params) + 1)
    params.append(limit)
    
    messages = await db.fetch(query, *params)
    
    return {
        "messages": list(reversed(messages)),
        "has_more": len(messages) == limit
    }

@app.post("/api/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user)
):
    """Create new conversation"""
    
    session_id = generate_id("session")
    
    await db.execute("""
        INSERT INTO conversations (session_id, user_id, title, started_at)
        VALUES ($1, $2, $3, NOW())
    """, session_id, current_user.user_id, request.title or "New Chat")
    
    return {
        "session_id": session_id,
        "title": request.title or "New Chat",
        "created_at": datetime.now().isoformat()
    }
```

### 6.4. Data Retention & Cleanup

```python
class HybridMemoryRetrieval:
    """Combine BM25 (keyword) + Semantic (vector) search"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = get_database()
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vector_store = PGVector(
            connection_string=DATABASE_URL,
            embedding_function=self.embeddings,
            collection_name="conversation_memories"
        )
    
    async def retrieve(self, query: str, k: int = 5) -> list:
        """Hybrid retrieval with re-ranking"""
        
        # Step 1: BM25 keyword search (PostgreSQL FTS)
        bm25_results = await self.db.fetch("""
            SELECT 
                memory_id,
                content,
                memory_type,
                importance_score,
                ts_rank(to_tsvector('english', content), 
                        plainto_tsquery('english', $1)) as bm25_score
            FROM conversation_memories
            WHERE user_id = $2
              AND is_deleted = FALSE
              AND to_tsvector('english', content) @@ plainto_tsquery('english', $1)
            ORDER BY bm25_score DESC
            LIMIT $3
        """, query, self.user_id, k)
        
        # Step 2: Semantic vector search
        semantic_results = self.vector_store.similarity_search_with_score(
            query,
            k=k,
            filter={
                "user_id": self.user_id,
                "is_deleted": False
            }
        )
        
        # Step 3: Combine and re-rank
        combined = self._merge_results(bm25_results, semantic_results)
        
        # Step 4: Re-rank using cross-encoder (optional)
        reranked = await self._rerank(query, combined, top_k=k)
        
        # Step 5: Update access tracking
        await self._track_access(reranked)
        
        return reranked
    
    def _merge_results(self, bm25_results, semantic_results):
        """Reciprocal Rank Fusion (RRF)"""
        from collections import defaultdict
        
        scores = defaultdict(float)
        content_map = {}
        
        # BM25 scores (weight: 0.3)
        for i, row in enumerate(bm25_results):
            memory_id = row['memory_id']
            scores[memory_id] += 0.3 / (i + 1)
            content_map[memory_id] = row
        
        # Semantic scores (weight: 0.7)
        for i, (doc, score) in enumerate(semantic_results):
            memory_id = doc.metadata['memory_id']
            scores[memory_id] += 0.7 / (i + 1)
            if memory_id not in content_map:
                content_map[memory_id] = {
                    'memory_id': memory_id,
                    'content': doc.page_content,
                    'memory_type': doc.metadata['memory_type'],
                    'importance_score': doc.metadata['importance_score']
                }
        
        # Sort by combined score
        sorted_results = sorted(
            scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [content_map[memory_id] for memory_id, _ in sorted_results]
    
    async def _rerank(self, query: str, candidates: list, top_k: int):
        """Re-rank using cross-encoder model (optional)"""
        from sentence_transformers import CrossEncoder
        
        model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')
        
        pairs = [[query, c['content']] for c in candidates]
        scores = model.predict(pairs)
        
        # Combine with importance score
        for i, candidate in enumerate(candidates):
            candidate['final_score'] = (
                0.8 * scores[i] + 
                0.2 * candidate['importance_score']
            )
        
        return sorted(candidates, key=lambda x: x['final_score'], reverse=True)[:top_k]
    
    async def _track_access(self, results: list):
        """Track which memories are accessed"""
        memory_ids = [r['memory_id'] for r in results]
        
        await self.db.execute("""
            UPDATE conversation_memories
            SET access_count = access_count + 1,
                last_accessed = NOW()
            WHERE memory_id = ANY($1)
        """, memory_ids)
```

### 6.3. Data Retention & Cleanup

```python
class DataRetentionManager:
    """Handle data lifecycle according to user preferences"""
    
    async def run_daily_cleanup(self):
        """Daily scheduled task"""
        
        # 1. Soft delete old conversations
        await self.archive_old_conversations()
        
        # 2. Hard delete expired data (GDPR compliance)
        await self.purge_expired_data()
        
        # 3. Vacuum pgvector index
        await self.optimize_vector_index()
        
        # 4. Generate analytics snapshots
        await self.create_analytics_snapshot()
    
    async def archive_old_conversations(self):
        """Move old conversations to archive status"""
        await self.db.execute("""
            UPDATE conversations c
            SET status = 'archived'
            WHERE c.last_message_at < NOW() - INTERVAL '90 days'
              AND c.status = 'active'
              AND c.user_id IN (
                  SELECT user_id FROM users 
                  WHERE data_retention_days = 90
              )
        """)
    
    async def purge_expired_data(self):
        """Hard delete data past retention period"""
        
        # Get users who want data deleted after retention period
        users_to_purge = await self.db.fetch("""
            SELECT user_id, data_retention_days
            FROM users
            WHERE last_active < NOW() - INTERVAL '1 year'
               OR data_retention_days IS NOT NULL
        """)
        
        for user in users_to_purge:
            retention_days = user['data_retention_days'] or 365
            
            # Delete old memories
            await self.db.execute("""
                DELETE FROM conversation_memories
                WHERE user_id = $1
                  AND created_at < NOW() - INTERVAL '$2 days'
            """, user['user_id'], retention_days)
            
            # Delete old messages
            await self.db.execute("""
                DELETE FROM messages
                WHERE user_id = $1
                  AND timestamp < NOW() - INTERVAL '$2 days'
            """, user['user_id'], retention_days)
    
    async def optimize_vector_index(self):
        """Rebuild pgvector HNSW index for performance"""
        await self.db.execute("""
            REINDEX INDEX CONCURRENTLY idx_mem_user_embedding;
        """)
        
        # Vacuum to reclaim space
        await self.db.execute("VACUUM ANALYZE conversation_memories;")
```

---

## 7. TỐI ƯU HÓA VÒNG LẶP DỮ LIỆU

### 7.1. The Data Flywheel Concept

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA FLYWHEEL CYCLE                           │
└─────────────────────────────────────────────────────────────────┘

        ┌──────────────────────┐
        │   1. USER INPUT      │
        │  (Conversations)     │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │   2. DATA CAPTURE    │
        │  (Store + Embed)     │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │   3. LEARNING        │
        │  (Pattern Analysis)  │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ 4. PERSONALIZATION   │
        │  (Better Responses)  │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ 5. USER SATISFACTION │
        │  (More Engagement)   │
        └──────────┬───────────┘
                   │
                   └─────────────► LOOP BACK TO 1

Flywheel Effect: Càng nhiều data → Càng cá nhân hóa → 
                 Càng hài lòng → Càng dùng nhiều → Càng nhiều data
```

### 7.2. Implementation Strategy

#### **Phase 1: Data Collection (Hiện tại)**

```python
class DataCollectionOptimizer:
    """Maximize data quality and quantity"""
    
    async def enhance_data_capture(self, conversation_state):
        """Extract maximum value from each conversation"""
        
        # 1. Explicit facts (user stated)
        explicit_facts = await self.extract_explicit_facts(
            conversation_state["message"]
        )
        
        # 2. Implicit signals (inferred)
        implicit_signals = await self.infer_implicit_signals(
            conversation_state["message"],
            conversation_state["response"]
        )
        
        # 3. Emotional context
        emotion_data = await self.analyze_emotion(
            conversation_state["message"]
        )
        
        # 4. Conversation patterns
        patterns = await self.detect_patterns(
            conversation_state["session_id"]
        )
        
        return {
            "explicit": explicit_facts,
            "implicit": implicit_signals,
            "emotion": emotion_data,
            "patterns": patterns
        }
    
    async def extract_explicit_facts(self, message: str):
        """Extract clear facts user mentioned"""
        
        # Use LLM to extract structured data
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Extract facts from user message.
                Return JSON array of facts with format:
                [
                    {"type": "preference|goal|constraint|context", 
                     "content": "...", 
                     "confidence": 0.0-1.0}
                ]"""},
                {"role": "user", "content": message}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def infer_implicit_signals(self, user_msg: str, ai_response: str):
        """Infer unstated preferences from behavior"""
        
        signals = []
        
        # Example: If user asks follow-up questions → topic interest
        if "?" in user_msg:
            signals.append({
                "type": "topic_interest",
                "content": "User showing interest in current topic",
                "confidence": 0.6
            })
        
        # Example: Response length preference
        response_length = len(ai_response.split())
        if not await self.user_requested_shorter_response(user_msg):
            signals.append({
                "type": "preference",
                "content": f"User accepts responses ~{response_length} words",
                "confidence": 0.5
            })
        
        return signals
```

#### **Phase 2: Learning & Pattern Recognition**

```python
class PatternLearningEngine:
    """Learn from accumulated data"""
    
    async def analyze_user_patterns(self, user_id: str):
        """Discover patterns in user behavior"""
        
        # 1. Temporal patterns (when user is active)
        temporal = await self.analyze_temporal_patterns(user_id)
        
        # 2. Topic preferences (what user talks about)
        topics = await self.analyze_topic_preferences(user_id)
        
        # 3. Communication style (how user prefers responses)
        style = await self.analyze_communication_style(user_id)
        
        # 4. Emotional patterns (mood trends)
        emotions = await self.analyze_emotional_trends(user_id)
        
        return {
            "temporal": temporal,
            "topics": topics,
            "style": style,
            "emotions": emotions
        }
    
    async def analyze_temporal_patterns(self, user_id: str):
        """When is user most active?"""
        
        activity = await self.db.fetch("""
            SELECT 
                EXTRACT(HOUR FROM timestamp) as hour,
                EXTRACT(DOW FROM timestamp) as day_of_week,
                COUNT(*) as message_count
            FROM messages
            WHERE user_id = $1
              AND timestamp > NOW() - INTERVAL '30 days'
            GROUP BY hour, day_of_week
            ORDER BY message_count DESC
        """, user_id)
        
        return {
            "peak_hours": [row['hour'] for row in activity[:3]],
            "peak_days": [row['day_of_week'] for row in activity[:3]]
        }
    
    async def analyze_topic_preferences(self, user_id: str):
        """What topics does user engage with most?"""
        
        # Use LLM to categorize historical conversations
        memories = await self.db.fetch("""
            SELECT content, memory_type, access_count
            FROM conversation_memories
            WHERE user_id = $1
            ORDER BY access_count DESC, importance_score DESC
            LIMIT 100
        """, user_id)
        
        # Cluster topics using LLM
        topic_analysis = await self.cluster_topics(memories)
        
        return topic_analysis
    
    async def analyze_communication_style(self, user_id: str):
        """How does user prefer to communicate?"""
        
        messages = await self.db.fetch("""
            SELECT content, role
            FROM messages
            WHERE user_id = $1
              AND timestamp > NOW() - INTERVAL '30 days'
            ORDER BY timestamp DESC
            LIMIT 100
        """, user_id)
        
        user_messages = [m['content'] for m in messages if m['role'] == 'user']
        
        return {
            "avg_length": sum(len(m.split()) for m in user_messages) / len(user_messages),
            "formality": await self.detect_formality(user_messages),
            "emoji_usage": any('😊' in m or '🙂' in m for m in user_messages)
        }
```

#### **Phase 3: Personalization Engine**

```python
class PersonalizationEngine:
    """Apply learned patterns to improve responses"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.patterns = None
    
    async def load_user_patterns(self):
        """Load pre-computed patterns"""
        self.patterns = await PatternLearningEngine().analyze_user_patterns(
            self.user_id
        )
    
    async def personalize_prompt(self, base_prompt: str, context: dict):
        """Modify system prompt based on user patterns"""
        
        if not self.patterns:
            await self.load_user_patterns()
        
        # Build personalized instructions
        personalization = f"""
User Communication Preferences:
- Preferred response length: ~{self.patterns['style']['avg_length']} words
- Communication style: {'formal' if self.patterns['style']['formality'] > 0.7 else 'casual'}
- Topics of interest: {', '.join(self.patterns['topics']['top_topics'][:3])}

Current mood indicators: {context.get('emotion', 'neutral')}

Adapt your response to match these preferences while maintaining helpfulness.
"""
        
        return base_prompt + "\n\n" + personalization
    
    async def personalize_memory_retrieval(self, query: str):
        """Adjust retrieval strategy based on patterns"""
        
        # Boost memories from preferred topics
        topic_boost = {
            topic: 1.5 
            for topic in self.patterns['topics']['top_topics'][:3]
        }
        
        # Retrieve with topic boosting
        retriever = HybridMemoryRetrieval(self.user_id)
        results = await retriever.retrieve(query, k=10)
        
        # Re-score based on topic match
        for result in results:
            memory_topic = result.get('memory_type')
            if memory_topic in topic_boost:
                result['final_score'] *= topic_boost[memory_topic]
        
        # Return top 5 after re-scoring
        return sorted(results, key=lambda x: x['final_score'], reverse=True)[:5]
```

#### **Phase 4: Feedback Loop**

```python
class FeedbackLoop:
    """Close the loop: measure satisfaction → improve system"""
    
    async def collect_implicit_feedback(self, conversation_state):
        """Infer satisfaction from user behavior"""
        
        signals = {
            "conversation_continued": False,
            "follow_up_question": False,
            "positive_language": False,
            "session_duration_seconds": 0
        }
        
        # Check if user continued conversation
        next_message = await self.db.fetchrow("""
            SELECT message_id FROM messages
            WHERE session_id = $1
              AND timestamp > $2
              AND role = 'user'
            ORDER BY timestamp ASC
            LIMIT 1
        """, conversation_state["session_id"], datetime.now())
        
        signals["conversation_continued"] = next_message is not None
        
        # Detect positive language
        positive_indicators = ["thanks", "thank you", "great", "perfect", "helpful"]
        signals["positive_language"] = any(
            indicator in conversation_state["message"].lower() 
            for indicator in positive_indicators
        )
        
        return signals
    
    async def update_memory_importance(self, feedback_signals):
        """Boost importance of memories that led to positive outcomes"""
        
        if feedback_signals["positive_language"]:
            # Boost recently accessed memories
            await self.db.execute("""
                UPDATE conversation_memories
                SET importance_score = LEAST(importance_score * 1.2, 1.0)
                WHERE user_id = $1
                  AND last_accessed > NOW() - INTERVAL '5 minutes'
            """, self.user_id)
    
    async def learn_from_negative_feedback(self, feedback):
        """Adjust system when user is unsatisfied"""
        
        if feedback["rating"] <= 2:
            # Mark recent memories as potentially incorrect
            await self.db.execute("""
                UPDATE conversation_memories
                SET metadata = jsonb_set(
                    metadata, 
                    '{needs_review}', 
                    'true'
                )
                WHERE user_id = $1
                  AND last_accessed > NOW() - INTERVAL '5 minutes'
            """, feedback["user_id"])
```

### 7.3. Measuring Flywheel Velocity

```python
class FlywheelMetrics:
    """Track how well the flywheel is spinning"""
    
    async def calculate_flywheel_metrics(self):
        """Measure data flywheel health"""
        
        metrics = {}
        
        # 1. Data Growth Rate
        metrics["data_growth"] = await self.db.fetchval("""
            SELECT COUNT(*) 
            FROM conversation_memories
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        
        # 2. Memory Utilization Rate (how often memories are used)
        metrics["memory_utilization"] = await self.db.fetchval("""
            SELECT AVG(access_count)
            FROM conversation_memories
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        
        # 3. User Engagement Trend
        metrics["engagement_trend"] = await self.db.fetch("""
            SELECT 
                DATE_TRUNC('day', timestamp) as day,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(*) as total_messages
            FROM messages
            WHERE timestamp > NOW() - INTERVAL '30 days'
            GROUP BY day
            ORDER BY day
        """)
        
        # 4. Personalization Quality (% of responses using retrieved context)
        metrics["personalization_rate"] = await self.db.fetchval("""
            SELECT 
                COUNT(*) FILTER (WHERE metadata->>'retrieved_context_count' > '0')::float /
                NULLIF(COUNT(*), 0)
            FROM messages
            WHERE role = 'assistant'
              AND timestamp > NOW() - INTERVAL '7 days'
        """)
        
        # 5. User Satisfaction Trend
        metrics["satisfaction_trend"] = await self.db.fetch("""
            SELECT 
                DATE_TRUNC('day', created_at) as day,
                AVG(rating) as avg_rating
            FROM feedback
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY day
            ORDER BY day
        """)
        
        return metrics
    
    def calculate_flywheel_velocity(self, metrics):
        """Single score: how fast is the flywheel spinning?"""
        
        # Weighted score combining all factors
        velocity = (
            0.2 * min(metrics["data_growth"] / 1000, 1.0) +  # Data growth
            0.2 * min(metrics["memory_utilization"] / 5, 1.0) +  # Memory use
            0.3 * metrics["personalization_rate"] +  # Personalization
            0.3 * (metrics["satisfaction_trend"][-1]["avg_rating"] / 5.0)  # Satisfaction
        )
        
        return velocity
```

### 7.4. Optimization Strategies

```yaml
# Flywheel Optimization Playbook

1. Increase Data Velocity:
   strategies:
     - Prompt users to share preferences during onboarding
     - Ask clarifying questions to extract more context
     - Implement "Tell me more about..." suggestions
     - Track implicit signals (click patterns, time spent)
   
   metrics:
     - New memories created per conversation
     - Conversation depth (avg messages per session)

2. Improve Data Quality:
   strategies:
     - Validate extracted facts with confidence scores
     - Cross-reference new info with existing memories
     - Implement conflict resolution for contradictions
     - Prune low-value memories (never accessed in 90 days)
   
   metrics:
     - Memory accuracy (validated vs total)
     - Memory access rate (% used at least once)

3. Enhance Learning:
   strategies:
     - Run weekly pattern analysis on all users
     - A/B test different personalization strategies
     - Implement transfer learning across similar users
     - Build topic clusters for better retrieval
   
   metrics:
     - Pattern detection accuracy
     - Personalization impact on satisfaction

4. Boost Engagement:
   strategies:
     - Proactive conversation starters based on patterns
     - Timely nudges during peak activity hours
     - Suggest topics from user's interest graph
     - Celebrate milestones (100th conversation, etc.)
   
   metrics:
     - Daily/weekly active users
     - Messages per user per week
     - Session duration

5. Close Feedback Loop:
   strategies:
     - In-chat feedback buttons (👍👎)
     - Periodic "How are we doing?" surveys
     - Implicit feedback from behavior
     - Use feedback to retrain retrieval weights
   
   metrics:
     - Feedback collection rate
     - Week-over-week satisfaction trend
```

---

## 8. SECURITY & PRIVACY

### 8.1. Data Isolation Architecture

```python
class UserDataIsolation:
    """Ensure complete separation of user data"""
    
    @staticmethod
    async def set_user_context(user_id: str):
        """Set PostgreSQL session variable for RLS"""
        await db.execute(f"SET app.current_user_id = '{user_id}'")
    
    @staticmethod
    async def validate_data_access(user_id: str, resource_id: str):
        """Verify user owns the resource"""
        
        owner = await db.fetchval("""
            SELECT user_id FROM conversation_memories
            WHERE memory_id = $1
        """, resource_id)
        
        if owner != user_id:
            raise PermissionError("Access denied: resource belongs to another user")
    
    @staticmethod
    async def audit_cross_user_access():
        """Daily audit to detect any data leakage"""
        
        violations = await db.fetch("""
            SELECT 
                cm.user_id as memory_owner,
                m.user_id as accessor,
                COUNT(*) as violation_count
            FROM conversation_memories cm
            JOIN messages m ON m.metadata->>'retrieved_memory_ids' @> 
                              jsonb_build_array(cm.memory_id::text)
            WHERE cm.user_id != m.user_id
            GROUP BY cm.user_id, m.user_id
        """)
        
        if violations:
            # CRITICAL: Alert security team
            await alert_security_team(violations)
```

### 8.2. PII Encryption

```python
from cryptography.fernet import Fernet
import os

class PIIEncryption:
    """Encrypt sensitive user data"""
    
    def __init__(self):
        # Key should be stored in environment variable
        self.key = os.environ.get("ENCRYPTION_KEY").encode()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> bytes:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode())
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data).decode()

# Usage
encryptor = PIIEncryption()

# Store user profile
encrypted_profile = encryptor.encrypt(json.dumps(user_profile))
await db.execute("""
    UPDATE users
    SET profile_data_encrypted = $1
    WHERE user_id = $2
""", encrypted_profile, user_id)

# Retrieve user profile
encrypted = await db.fetchval("""
    SELECT profile_data_encrypted FROM users WHERE user_id = $1
""", user_id)
profile = json.loads(encryptor.decrypt(encrypted))
```

---

## 9. MONITORING & ANALYTICS

### 9.1. Real-time Metrics Dashboard

```python
class MetricsDashboard:
    """Track system health and performance"""
    
    async def get_realtime_metrics(self):
        """Metrics for ops dashboard"""
        
        return {
            "system_health": {
                "api_latency_p99": await self.get_latency_p99(),
                "error_rate": await self.get_error_rate(),
                "active_connections": await self.get_active_connections()
            },
            "business_metrics": {
                "active_users_1h": await self.get_active_users(hours=1),
                "conversations_started_today": await self.get_conversations_today(),
                "avg_messages_per_conversation": await self.get_avg_messages()
            },
            "data_metrics": {
                "total_memories": await self.get_total_memories(),
                "memories_created_today": await self.get_memories_today(),
                "vector_search_qps": await self.get_vector_search_qps()
            },
            "llm_metrics": {
                "total_tokens_today": await self.get_tokens_today(),
                "estimated_cost_usd": await self.calculate_llm_cost(),
                "avg_generation_time_ms": await self.get_avg_generation_time()
            }
        }
```

---

## 10. DEPLOYMENT CONFIGURATION

### 10.1. Railway Deployment Structure

```yaml
# railway.toml

[build]
builder = "NIXPACKS"

# Frontend Service (React + Vite)
[[services]]
name = "frontend"
source = "./frontend"

[services.frontend.build]
buildCommand = "pnpm install && pnpm build"
startCommand = "pnpm preview"

[services.frontend.env]
VITE_API_URL = "${{API_URL}}"
VITE_WS_URL = "${{WS_URL}}"
NODE_ENV = "production"

[services.frontend.healthcheck]
path = "/"
interval = 30
timeout = 10

# Backend API Service (FastAPI)
[[services]]
name = "api"
source = "./backend"

[services.api.build]
buildCommand = "pip install -r requirements.txt"
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4"

[services.api.env]
DATABASE_URL = "${{DATABASE_URL}}"
REDIS_URL = "${{REDIS_URL}}"
OPENAI_API_KEY = "${{OPENAI_API_KEY}}"
JWT_SECRET = "${{JWT_SECRET}}"
ENCRYPTION_KEY = "${{ENCRYPTION_KEY}}"

[services.api.healthcheck]
path = "/health"
interval = 30
timeout = 10

# PostgreSQL Database
[[services]]
name = "postgres"
type = "database"
engine = "postgresql"
version = "16"

[services.postgres.volume]
mountPath = "/var/lib/postgresql/data"
size = "10GB"

# Redis (for caching & rate limiting)
[[services]]
name = "redis"
type = "database"
engine = "redis"
version = "7"

# Cron Service (background tasks)
[[services]]
name = "cron"
source = "./backend"

[services.cron.build]
buildCommand = "pip install -r requirements.txt"
startCommand = "python -m celery -A tasks worker --beat"

[services.cron.env]
DATABASE_URL = "${{DATABASE_URL}}"
REDIS_URL = "${{REDIS_URL}}"
```

### 10.2. Frontend Build Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt', 'apple-touch-icon.png'],
      manifest: {
        name: 'AI Chatbot',
        short_name: 'ChatAI',
        description: 'Personalized AI Assistant',
        theme_color: '#ffffff',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
          'query-vendor': ['@tanstack/react-query'],
          'socket': ['socket.io-client']
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: process.env.VITE_WS_URL || 'ws://localhost:8000',
        ws: true
      }
    }
  }
});
```

### 10.3. Nginx Configuration (Production)

```nginx
# nginx.conf for React SPA + FastAPI

upstream api_backend {
    server api:8000;
}

upstream websocket_backend {
    server api:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # React static files
    location / {
        root /var/www/frontend/dist;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket endpoint
    location /ws/ {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
```

### 10.4. Docker Compose (Local Development)

```yaml
# docker-compose.yml

version: '3.8'

services:
  # Frontend (React + Vite)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:8000
      - VITE_WS_URL=ws://localhost:8000
    depends_on:
      - api
  
  # Backend API (FastAPI)
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/chatbot
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - postgres
      - redis
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
  
  # PostgreSQL + pgvector
  postgres:
    image: ankane/pgvector:latest
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=chatbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
  
  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 10.5. Environment Variables

```bash
# .env.example

# Frontend
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
VITE_APP_NAME="AI Chatbot"

# Backend
DATABASE_URL=postgresql://user:password@postgres:5432/chatbot
REDIS_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# Security
JWT_SECRET=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

ENCRYPTION_KEY=your-fernet-encryption-key-32-bytes

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,http://localhost:5173

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Monitoring
SENTRY_DSN=https://...
SENTRY_ENVIRONMENT=production
```

---

## KẾT LUẬN

Báo cáo này mô tả chi tiết:

✅ **Frontend React.js hiện đại** với WebSocket real-time, TypeScript, Zustand state management  
✅ **Luồng dữ liệu đầu vào/ra** rõ ràng với JSON Schema chuẩn  
✅ **Cấu trúc Database** với PostgreSQL + pgvector tối ưu cho user isolation  
✅ **Quy trình vận hành** từ Collection → Processing → Storage → Retention  
✅ **Data Flywheel** tạo vòng lặp tích cực: Data → Learning → Personalization → Engagement → More Data  
✅ **Security & Privacy** đảm bảo data isolation tuyệt đối  
✅ **Monitoring** để track hiệu quả của hệ thống  
✅ **Deployment** trên Railway với Docker, Nginx  

**Điểm mạnh của thiết kế này:**

### Frontend (React.js):
1. **Real-time streaming** responses với WebSocket + Server-Sent Events
2. **Type-safe** với TypeScript cho toàn bộ codebase
3. **Optimistic updates** cho UX mượt mà
4. **Component-based** architecture dễ maintain và scale
5. **PWA support** - có thể install như app native
6. **Infinite scroll** message history với pagination
7. **Modern UI** với shadcn/ui + Tailwind CSS

### Backend Architecture:
1. User data hoàn toàn isolated (RLS + explicit filtering)
2. Hybrid search (BM25 + Semantic) cho retrieval tốt nhất
3. Vòng lặp dữ liệu tự cải thiện theo thời gian
4. Tuân thủ GDPR với data retention policies
5. FastAPI async với WebSocket support
6. LangGraph orchestration cho complex workflows

### Data Flow:
1. **Input**: React → FastAPI → LangGraph → LLM
2. **Processing**: Guardrails → Memory Retrieval → Generation
3. **Output**: Streaming response → pgvector storage → Analytics
4. **Feedback Loop**: User satisfaction → Pattern learning → Personalization

**Tech Stack Summary:**

```
┌─────────────────────────────────────────────┐
│ FRONTEND: React 18 + TypeScript             │
│ - State: Zustand + React Query              │
│ - UI: shadcn/ui + Tailwind                  │
│ - Real-time: Socket.IO + SSE                │
└─────────────────────────────────────────────┘
                    ↓ WebSocket/HTTPS
┌─────────────────────────────────────────────┐
│ BACKEND: FastAPI (Python 3.11)              │
│ - Orchestration: LangGraph 0.2+             │
│ - LLM: GPT-4o (friend) + GPT-4o-mini        │
│ - Guardrails: NeMo-Guardrails               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ DATA LAYER: PostgreSQL 16 + pgvector        │
│ - Embeddings: text-embedding-3-small        │
│ - Encryption: AES-256 + Fernet              │
│ - Search: BM25 + Semantic (hybrid)          │
└─────────────────────────────────────────────┘
```
