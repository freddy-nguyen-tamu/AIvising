from typing import Dict, List
from app.schemas import Conversation, Document, FeedbackItem, Message


class InMemoryDB:
    def __init__(self) -> None:
        self.conversations: Dict[int, Conversation] = {}
        self.documents: Dict[int, Document] = {}
        self.feedback: Dict[int, FeedbackItem] = {}

        self._conversation_id = 1
        self._document_id = 1
        self._feedback_id = 1

    def seed(self) -> None:
        if self.documents:
            return

        self.add_document(
            title="Remote Work Policy",
            category="Policy",
            content=(
                "Employees may work remotely up to three days per week with manager approval. "
                "Core collaboration hours are 10 AM to 3 PM local time. Team meetings should "
                "be attended unless approved otherwise."
            ),
        )
        self.add_document(
            title="New Hire Onboarding Checklist",
            category="Onboarding",
            content=(
                "During week one, new hires should complete account setup, security training, "
                "tool access requests, and a team introduction. Managers should schedule a 30-60-90 day plan review."
            ),
        )
        self.add_document(
            title="Incident Escalation Process",
            category="Support",
            content=(
                "Critical issues should be escalated immediately to the on-call lead. "
                "Document impact, affected systems, customer visibility, and mitigation steps in the incident record."
            ),
        )
        self.add_document(
            title="Design Review Workflow",
            category="Product",
            content=(
                "Design reviews should include the problem statement, target user, current pain points, "
                "wireframes, accessibility considerations, and implementation constraints before engineering handoff."
            ),
        )

    def add_document(self, title: str, content: str, category: str) -> Document:
        doc = Document(
            id=self._document_id,
            title=title,
            content=content,
            category=category,
        )
        self.documents[self._document_id] = doc
        self._document_id += 1
        return doc

    def list_documents(self) -> List[Document]:
        return list(self.documents.values())

    def create_conversation(self, role: str, first_user_message: str) -> Conversation:
        title = first_user_message[:48].strip() or "New conversation"
        convo = Conversation(
            id=self._conversation_id,
            title=title,
            role=role,
            messages=[Message(role="user", content=first_user_message)],
        )
        self.conversations[self._conversation_id] = convo
        self._conversation_id += 1
        return convo

    def get_conversation(self, conversation_id: int) -> Conversation:
        return self.conversations[conversation_id]

    def list_conversations(self) -> List[Conversation]:
        return list(self.conversations.values())

    def add_message(self, conversation_id: int, role: str, content: str) -> None:
        self.conversations[conversation_id].messages.append(
            Message(role=role, content=content)
        )

    def add_feedback(self, conversation_id: int, message_index: int, value: int) -> FeedbackItem:
        item = FeedbackItem(
            id=self._feedback_id,
            conversation_id=conversation_id,
            message_index=message_index,
            value=value,
        )
        self.feedback[self._feedback_id] = item
        self._feedback_id += 1
        return item

    def list_feedback(self) -> List[FeedbackItem]:
        return list(self.feedback.values())


db = InMemoryDB()
