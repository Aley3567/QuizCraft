"""数据模型测试：覆盖 Document -> Section -> Concept -> Question -> QuizSession -> Answer 关系链。"""
import pytest
from sqlalchemy import select

from quizcraft.models import Answer, Concept, Document, Question, QuizSession, Section
from quizcraft.models.document import DocumentStatus
from quizcraft.models.quiz import QuestionType, SessionStatus


async def test_create_document_defaults(session):
    """Document 建表 + 默认值：status=pending，created_at 自动填充。"""
    doc = Document(filename="lecture1.pdf")
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    assert doc.id is not None
    assert doc.status == DocumentStatus.PENDING
    assert doc.created_at is not None
    assert doc.updated_at is not None


async def test_section_belongs_to_document(session):
    doc = Document(filename="lec.pdf")
    session.add(doc)
    await session.flush()

    section = Section(
        document_id=doc.id,
        section_path="第2章 > 2.1 节",
        page_number=12,
        content="光合作用是植物利用光能合成有机物的过程。",
        order_index=0,
        token_count=200,
    )
    session.add(section)
    await session.commit()

    loaded = (
        await session.execute(select(Section).where(Section.document_id == doc.id))
    ).scalar_one()
    assert loaded.section_path == "第2章 > 2.1 节"
    assert loaded.page_number == 12
    assert loaded.token_count == 200


async def test_full_graph_document_to_answer(session):
    """完整链路：文档 -> 分块 -> 概念 -> 题目 -> 答题会话 -> 作答，验证外键与 JSON 字段存取。"""
    doc = Document(filename="lec.pdf", page_count=30, status=DocumentStatus.COMPLETE)
    session.add(doc)
    await session.flush()

    section = Section(
        document_id=doc.id,
        section_path="第2章 > 2.1 节",
        page_number=12,
        content="光合作用是植物利用光能合成有机物的过程。",
        order_index=0,
    )
    session.add(section)
    await session.flush()

    source_span = {"page": 12, "section_path": "第2章 > 2.1 节", "text": "光合作用是..."}
    concept = Concept(
        document_id=doc.id,
        section_id=section.id,
        name="光合作用",
        description="植物利用光能合成有机物",
        source_span=source_span,
        bloom_level="Understand",
    )
    session.add(concept)
    await session.flush()

    question = Question(
        document_id=doc.id,
        concept_id=concept.id,
        section_id=section.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        stem="光合作用主要发生在植物的哪个部位？",
        options=["根部", "叶片", "茎", "花"],
        correct_option_index=1,
        explanation="叶片含有叶绿体，是光合作用的主要场所。",
        source_span=source_span,
        bloom_level="Understand",
        difficulty="easy",
        self_eval_score=0.9,
    )
    session.add(question)
    await session.flush()

    quiz = QuizSession(
        document_id=doc.id,
        question_ids=[question.id],
        status=SessionStatus.IN_PROGRESS,
    )
    session.add(quiz)
    await session.flush()

    answer = Answer(
        quiz_session_id=quiz.id,
        question_id=question.id,
        selected_option_index=0,  # 选了"根部"，错误
        is_correct=False,
        feedback="你的课件第 12 页提到：光合作用是...主要发生在叶片。",
    )
    session.add(answer)
    await session.commit()

    # 反查整条链
    loaded_doc = (
        await session.execute(select(Document).where(Document.id == doc.id))
    ).scalar_one()
    assert loaded_doc.page_count == 30

    loaded_q = (
        await session.execute(select(Question).where(Question.id == question.id))
    ).scalar_one()
    assert loaded_q.question_type == QuestionType.MULTIPLE_CHOICE
    assert loaded_q.options == ["根部", "叶片", "茎", "花"]
    assert loaded_q.correct_option_index == 1
    assert loaded_q.source_span == source_span
    assert loaded_q.self_eval_score == pytest.approx(0.9)

    loaded_ans = (
        await session.execute(select(Answer).where(Answer.question_id == question.id))
    ).scalar_one()
    assert loaded_ans.is_correct is False
    assert "第 12 页" in loaded_ans.feedback

    loaded_quiz = (
        await session.execute(select(QuizSession).where(QuizSession.id == quiz.id))
    ).scalar_one()
    assert loaded_quiz.question_ids == [question.id]
    assert loaded_quiz.status == SessionStatus.IN_PROGRESS


async def test_question_source_span_is_required_field(session):
    """source_span 是 QuizCraft 核心数据基础，题目必须能存文档原文位置。"""
    doc = Document(filename="lec.pdf")
    session.add(doc)
    await session.flush()

    q = Question(
        document_id=doc.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        stem="题干",
        options=["A", "B"],
        correct_option_index=0,
        source_span={"page": 1, "section_path": "intro", "text": "原文"},
    )
    session.add(q)
    await session.commit()
    await session.refresh(q)

    assert q.source_span["page"] == 1
    assert q.source_span["text"] == "原文"
