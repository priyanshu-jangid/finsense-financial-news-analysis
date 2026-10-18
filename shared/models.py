from datetime import datetime, UTC

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    watchlist: Mapped[list["Watchlist"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )
    # Relationship to articles for test compatibility
    articles: Mapped[list["Article"]] = relationship(
        "Article",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    sector: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    watchlist_entries: Mapped[list["Watchlist"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )

    article_entities: Mapped[list["ArticleEntity"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )

    sentiment_analyses: Mapped[list["SentimentAnalysis"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="watchlist",
    )

    company: Mapped["Company"] = relationship(
        back_populates="watchlist_entries",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "company_id",
            name="uq_user_company_watchlist",
        ),
    )


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    credibility_tier: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    articles: Mapped[list["Article"]] = relationship(
        back_populates="source",
    )


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id"),
        nullable=True,
    )
    # Added company association for sentiment aggregation tests
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"),
        nullable=True,
    )
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="articles",
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    url: Mapped[str | None] = mapped_column(
        String(2000),
        unique=True,
        nullable=True,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    canonical_article_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id"),
        nullable=True,
    )

    provider_id: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    author: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    source: Mapped["Source"] = relationship(
        back_populates="articles",
    )

    entities: Mapped[list["ArticleEntity"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        foreign_keys="ArticleEntity.article_id",
    )

    sentiments: Mapped[list["SentimentAnalysis"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        foreign_keys="SentimentAnalysis.article_id",
    )


class ArticleEntity(Base):
    __tablename__ = "article_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    article: Mapped["Article"] = relationship(
        back_populates="entities",
        foreign_keys=[article_id],
    )

    company: Mapped["Company"] = relationship(
        back_populates="article_entities",
    )

    __table_args__ = (
        UniqueConstraint(
            "article_id",
            "company_id",
            name="uq_article_company_entity",
        ),
    )


class IngestionCheckpoint(Base):
    __tablename__ = "ingestion_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    feed_type: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    last_successful_published_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_run_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="idle",
        nullable=False,
    )

    articles_fetched: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    articles_persisted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analyses"
    # Unique constraint removed to allow multiple sentiment records per article/company/model
    __table_args__ = (UniqueConstraint("article_id", "company_id", "model_used", name="uq_sentiment_article_company_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    article: Mapped["Article"] = relationship(
        back_populates="sentiments",
        foreign_keys=[article_id],
    )

    company: Mapped["Company"] = relationship(
        back_populates="sentiment_analyses",
    )
