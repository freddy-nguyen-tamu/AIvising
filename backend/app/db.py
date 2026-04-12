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
            title="Academic Probation Policy",
            content=(
                "Students on academic probation should meet with an academic advisor "
                "to create a success plan. Registration may be limited until advising is completed."
            ),
        )
        self.add_document(
            title="Transfer Credit Procedure",
            content=(
                "Transfer credits must be reviewed by the department. Students should submit "
                "official transcripts and any required course syllabi for evaluation."
            ),
        )
        self.add_document(
            title="Graduation Application Timeline",
            content=(
                "Students should apply for graduation before the published university deadline. "
                "Advisors should verify degree audit completion before final approval."
            ),
        )

    def add_document(self, title: str, content: str) -> Document:
        doc = Document(id=self._document_id, title=title, content=content)
        self.documents[self._document_id] = doc
        self._document_id += 1
        return doc

    def list_documents(self) -> List[Document]:
        return list(self.documents.values())

    def create_conversation(self, role: str, first_user_message: str) -> Conversation:
        title = first_user_message[:40].strip() or "New conversation"
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
