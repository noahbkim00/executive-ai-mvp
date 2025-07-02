# Executive AI MVP - Multi-Phase Conversation Flow Implementation Plan

## Project Overview

Transform the current basic ChatGPT-like interface into an intelligent executive search assistant that systematically collects job requirements through a structured conversation flow.

### Current State
- Basic chat interface (React + TypeScript)
- FastAPI backend with LangChain/OpenAI integration
- Simple message/response pattern
- Docker-based development environment

### Target State
- Multi-phase conversation flow for executive search
- Intelligent follow-up question generation
- Structured data collection for future LangGraph integration
- Progress indicators and enhanced UX
- Backward compatibility with existing chat

---

## Phase 1: Backend Foundation & Data Models

### Objectives
- Create data models for conversation state and job requirements
- Implement conversation state management
- Add database schema for persistent storage
- Maintain backward compatibility

### Tasks
1. **Data Models** (`backend/src/models/`)
   - `conversation.py`: Conversation state, phases, and flow management
   - `job_requirements.py`: Structured job requirement data
   - `company_info.py`: Company context and basic information
   - Update existing `chat.py` models as needed

2. **Database Schema** (`backend/alembic/`)
   - Create migration for conversation tables
   - Add job_requirements and company_info tables
   - Ensure proper relationships and indexing

3. **Services Layer** (`backend/src/services/`)
   - `conversation_service.py`: State management and phase transitions
   - `requirements_extraction_service.py`: Parse and structure initial requirements
   - Update `chat_service.py` to support conversation context

4. **API Endpoints** (`backend/src/routers/`)
   - Extend chat router with conversation state endpoints
   - Add endpoints for conversation status and data retrieval

### Success Criteria
- [ ] All data models defined with proper Pydantic validation
- [ ] Database migrations run successfully
- [ ] Conversation state persists between messages
- [ ] Existing chat functionality remains unchanged
- [ ] API tests pass for new endpoints

### Files to Create/Modify
- `backend/src/models/conversation.py` (new)
- `backend/src/models/job_requirements.py` (new) 
- `backend/src/models/company_info.py` (new)
- `backend/src/services/conversation_service.py` (new)
- `backend/src/services/requirements_extraction_service.py` (new)
- `backend/src/services/chat_service.py` (modify)
- `backend/src/routers/chat.py` (modify)
- `backend/alembic/versions/xxx_add_conversation_tables.py` (new)

---

## Phase 2: Intelligent Question Generation

### Objectives
- Implement LangChain prompts for follow-up question generation
- Create question validation and filtering logic
- Ensure questions focus on subjective criteria only
- Generate contextual, role-specific questions

### Tasks
1. **Prompt Engineering**
   - Design system prompts for question generation
   - Create templates for different role types (C-suite, VP, etc.)
   - Implement validation to avoid research-based questions

2. **Question Generation Service**
   - `question_generation_service.py`: Core question generation logic
   - Context-aware prompting based on collected information
   - Question categorization (cultural fit, experience, deal-breakers)

3. **Question Validation**
   - Filter out questions that can be researched online
   - Ensure questions uncover subjective requirements
   - Validate question relevance to role and company

4. **Testing & Refinement**
   - Create test cases for various job types
   - Validate question quality and relevance
   - Iterative prompt improvement

### Success Criteria
- [ ] Generates 3-5 relevant follow-up questions per conversation
- [ ] Questions focus on subjective criteria (cultural fit, specific experiences)
- [ ] No questions about company size, revenue, or other researchable data
- [ ] Questions are contextual to the specific role and company
- [ ] Question generation is fast (<2 seconds)

### Files to Create/Modify
- `backend/src/services/question_generation_service.py` (new)
- `backend/src/prompts/` (new directory)
  - `question_generation_prompts.py` (new)
  - `role_specific_templates.py` (new)
- `backend/tests/test_question_generation.py` (new)

---

## Phase 3: Frontend State Management & UI Enhancement

### Objectives
- Implement conversation state management in React
- Add progress indicators for multi-phase flow  
- Create specialized UI components for question phases
- Maintain responsive design and accessibility

### Tasks
1. **State Management**
   - Implement React context for conversation state
   - Add TypeScript types for conversation phases
   - Handle state persistence and synchronization

2. **UI Components**
   - `ConversationProgress.tsx`: Progress indicator component
   - `QuestionPhase.tsx`: Specialized component for Q&A phase
   - `RequirementsSummary.tsx`: Display collected requirements
   - Update existing chat components for phase awareness

3. **Enhanced Chat Experience**
   - Visual distinction between conversation phases
   - Progress bar showing question completion
   - Smooth transitions between phases
   - Loading states for question generation

4. **Responsive Design**
   - Ensure mobile compatibility
   - Test across different screen sizes
   - Maintain accessibility standards

### Success Criteria
- [ ] Clear visual indication of conversation phase
- [ ] Progress indicator shows question completion status
- [ ] Smooth transitions between conversation phases
- [ ] Responsive design works on mobile and desktop
- [ ] Existing chat functionality preserved
- [ ] Loading states provide good user experience

### Files to Create/Modify
- `ui/src/contexts/ConversationContext.tsx` (new)
- `ui/src/components/ConversationProgress.tsx` (new)
- `ui/src/components/QuestionPhase.tsx` (new)
- `ui/src/components/RequirementsSummary.tsx` (new)
- `ui/src/types/conversation.ts` (new)
- `ui/src/services/api.ts` (modify)
- `ui/src/components/ChatContainer.tsx` (modify)

---

## Phase 4: Integration & Complete Flow

### Objectives
- Integrate all components into complete conversation flow
- Implement end-to-end user journey
- Add error handling and edge cases
- Prepare data structure for future LangGraph integration

### Tasks
1. **Flow Integration**
   - Connect frontend state management with backend services
   - Implement complete user journey from initial message to completion
   - Add transition logic between phases

2. **Data Export Preparation**
   - Structure collected data for LangGraph consumption
   - Add data export endpoints
   - Implement conversation summary generation

3. **Error Handling & Edge Cases**
   - Handle network errors gracefully
   - Manage conversation timeout scenarios
   - Add retry logic for failed operations
   - Validate user inputs at each phase

4. **Testing & Polish**
   - End-to-end testing of complete flow
   - Performance optimization
   - UI/UX polish and refinement
   - Documentation updates

### Success Criteria
- [ ] Complete user journey works end-to-end
- [ ] Data is properly structured for future agent processing
- [ ] Robust error handling for all failure modes
- [ ] Performance is acceptable (<3s response times)
- [ ] User experience is smooth and intuitive
- [ ] All existing functionality remains intact

### Files to Create/Modify
- `backend/src/services/flow_orchestration_service.py` (new)
- `backend/src/services/data_export_service.py` (new)
- Multiple files across frontend and backend for integration

---

## Phase 5: Testing, Documentation & Deployment Prep

### Objectives
- Comprehensive testing suite
- Update documentation
- Prepare for production deployment
- Performance optimization

### Tasks
1. **Testing Suite**
   - Unit tests for all new services
   - Integration tests for conversation flow
   - Frontend component testing
   - End-to-end testing automation

2. **Documentation**
   - Update README with new features
   - API documentation updates
   - User guide for new conversation flow
   - Developer documentation for future enhancements

3. **Performance & Security**
   - Database query optimization
   - API response time optimization
   - Security review of new endpoints
   - Rate limiting and abuse prevention

4. **Deployment Preparation**
   - Production configuration
   - Environment variable management
   - Docker production setup
   - CI/CD pipeline updates

### Success Criteria
- [ ] >90% test coverage for new functionality
- [ ] All tests pass consistently
- [ ] Complete documentation for new features
- [ ] Performance benchmarks meet requirements
- [ ] Security review completed
- [ ] Production deployment guide ready

---

## Success Metrics

### Technical Metrics
- Response time <3 seconds for question generation
- >95% uptime and reliability
- Backward compatibility maintained
- Test coverage >90%

### User Experience Metrics
- Complete conversation flow in <5 minutes
- 3-5 relevant questions generated per session
- Questions uncover subjective requirements not provided initially
- Smooth transition between conversation phases

### Business Metrics
- Executive search professionals can complete requirement gathering efficiently
- Structured data enables future agent processing
- System extensible for LangGraph integration

---

## Risk Mitigation

### Technical Risks
- **LangChain/OpenAI API reliability**: Implement retry logic and fallback strategies
- **Database performance**: Optimize queries and add proper indexing
- **State management complexity**: Keep state simple and well-documented

### Product Risks
- **Question quality**: Extensive testing and prompt refinement
- **User adoption**: Maintain familiar chat interface with gradual enhancement
- **Scope creep**: Focus on core conversation flow, defer advanced features

---

## Timeline Estimates

- **Phase 1**: 3-4 days (Backend foundation)
- **Phase 2**: 2-3 days (Question generation)
- **Phase 3**: 3-4 days (Frontend enhancement)
- **Phase 4**: 2-3 days (Integration)
- **Phase 5**: 2-3 days (Testing & documentation)

**Total Estimated Timeline**: 12-17 days

---

## Change Log

### Initial Plan - 2024-07-02
- Created comprehensive implementation plan
- Defined 5 phases with clear success criteria
- Established technical and business metrics

### Phase 1 Completed - 2024-07-02
**Achievements:**
- ✅ All data models created with proper validation
- ✅ Database migrations set up with Alembic
- ✅ Conversation state management fully functional
- ✅ Requirements extraction using LangChain working
- ✅ API endpoints extended with backward compatibility
- ✅ All existing tests passing

**Learnings:**
- Need to handle psycopg2/asyncpg dependency conflict for Alembic
- Database initialization should be lazy to avoid import issues
- Metadata is a reserved column name in SQLAlchemy (renamed to conversation_metadata)

**Technical Decisions:**
- Used UUID for conversation IDs for better scalability
- Implemented enum-based phase tracking for clear state management
- Separated job requirements and company info into distinct models
- Used JSON columns for flexible list/dict storage in PostgreSQL

### Phase 2 Started - 2024-07-02
- Beginning intelligent question generation implementation
- Focus on LangChain prompts for contextual follow-up questions