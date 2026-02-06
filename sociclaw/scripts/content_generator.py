"""
Module for generating optimized content for X (Twitter) posts.

This module provides functionality to:
- Generate text optimized for X (max 280 chars or threads)
- Adapt tone based on post category
- Include relevant hashtags
- Generate image prompts for the configured image backend
"""

import logging
import json
import random
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

from .scheduler import PostPlan

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GeneratedPost:
    """
    Generated post with text, image prompt, and metadata.

    Attributes:
        text: Post text (280 chars or thread format)
        image_prompt: Prompt for image generation
        hashtags: List of hashtags to include
        category: Post category (e.g., "market_analysis")
        date: Publication date
        time: Publication time (hour in UTC)
    """
    text: str
    image_prompt: str
    hashtags: List[str] = field(default_factory=list)
    category: str = ""
    date: Optional[str] = None
    time: Optional[int] = None


class ContentGenerator:
    """
    Generate optimized content for X posts based on PostPlan.

    This class loads templates, generates text following X best practices,
    adapts tone by category, and creates image prompts for the image backend.
    """

    # Category-specific tone guidance
    TONES = {
        "market_analysis": "professional",
        "educational": "didactic",
        "news": "informative",
        "tips": "helpful",
        "opinion": "confident",
        "thread": "detailed",
        "meme": "casual"
    }

    # Maximum tweet length
    MAX_TWEET_LENGTH = 280

    def __init__(self, templates_path: Optional[Path] = None):
        """
        Initialize the ContentGenerator.

        Args:
            templates_path: Path to post_templates.json file.
                          If None, uses default location.
        """
        if templates_path is None:
            # Default to templates/ directory relative to this file
            templates_path = Path(__file__).parent.parent / "templates" / "post_templates.json"

        self.templates_path = templates_path
        self.templates: Dict[str, List[Dict]] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load post templates from JSON file."""
        try:
            if not self.templates_path.exists():
                logger.warning(f"Templates file not found at {self.templates_path}")
                self._create_default_templates()
                return

            with open(self.templates_path, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)

            logger.info(f"Loaded {len(self.templates)} template categories")
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            self._create_default_templates()

    def _create_default_templates(self) -> None:
        """Create minimal default templates if file doesn't exist."""
        self.templates = {
            "market_analysis": [
                {
                    "structure": "{topic} analysis: {insight}",
                    "example": "Bitcoin analysis: Testing critical $40k support level"
                }
            ],
            "educational": [
                {
                    "structure": "How to {action}: {tip}",
                    "example": "How to start in DeFi: Begin with stablecoins"
                }
            ],
            "news": [
                {
                    "structure": "Breaking: {headline}",
                    "example": "Breaking: Major exchange announces Base integration"
                }
            ],
            "tips": [
                {
                    "structure": "Pro tip: {advice}",
                    "example": "Pro tip: Always verify contract addresses"
                }
            ],
            "opinion": [
                {
                    "structure": "{hot_take} {reasoning}",
                    "example": "L2s will flip L1s. Lower fees = better UX."
                }
            ],
            "thread": [
                {
                    "structure": "Thread: {topic}\n\n1/ {intro}",
                    "example": "Thread: Understanding gas fees\n\n1/ Let's break it down"
                }
            ],
            "meme": [
                {
                    "structure": "{setup}\n\n{punchline}",
                    "example": "Me: I'll just check the charts\n\nAlso me: *still staring 3h later*"
                }
            ]
        }

    def generate_post(self, plan: PostPlan) -> GeneratedPost:
        """
        Generate a complete post from a PostPlan.

        Args:
            plan: PostPlan with date, time, category, topic, and hashtags

        Returns:
            GeneratedPost with text, image_prompt, and metadata
        """
        try:
            # Get templates for this category
            category_templates = self.templates.get(plan.category, [])
            if not category_templates:
                logger.warning(f"No templates for category {plan.category}")
                category_templates = list(self.templates.values())[0]

            # Select random template
            template = random.choice(category_templates)

            # Generate text
            text = self._generate_text(plan, template)

            # Generate image prompt
            image_prompt = self._generate_image_prompt(plan, text)

            # Create GeneratedPost
            post = GeneratedPost(
                text=text,
                image_prompt=image_prompt,
                hashtags=plan.hashtags[:3],  # Limit to 3 hashtags
                category=plan.category,
                date=plan.date.strftime("%Y-%m-%d"),
                time=plan.time
            )

            logger.info(f"Generated post for {plan.category}: {text[:50]}...")
            return post

        except Exception as e:
            logger.error(f"Error generating post: {e}")
            raise

    def _generate_text(self, plan: PostPlan, template: Dict) -> str:
        """
        Generate post text based on template and plan.

        Args:
            plan: PostPlan with topic and category
            template: Template dict with structure and examples

        Returns:
            Generated text string (max 280 chars or thread)
        """
        # Get tone for this category
        tone = self.TONES.get(plan.category, "professional")

        # Build text based on template structure
        if "structure" in template:
            # Simple replacement-based generation
            text = template["structure"]

            replacements = {
                "topic": plan.topic,
                "insight": "Key levels to watch",
                "trend": "Momentum building",
                "conclusion": "Watch for confirmation",
                "action": f"understand {plan.topic}",
                "tip": "Start with the basics",
                "headline": plan.topic,
                "impact": "Big implications ahead",
                "detail": "More details soon",
                "context": "Worth keeping on your radar",
                "advice": plan.topic,
                "benefit": "Security first",
                "reasoning": "Here's why it matters.",
                "hot_take": plan.topic,
                "statement": plan.topic,
                "intro": "Understanding the fundamentals",
                "point": "Key takeaway you can apply today",
                "opening": "Start with the core concept",
                "key_point": "Focus on risk management",
                "setup": plan.topic,
                "punchline": "Classic crypto move",
                "scenario": plan.topic,
                "explanation": "Keep it simple and consistent",
                "key_takeaway": "Safety and patience win",
            }

            for key, value in replacements.items():
                text = text.replace(f"{{{key}}}", value)

            # Replace any remaining placeholders
            text = re.sub(r"{[^}]+}", "details", text)
        else:
            # Fallback to example if no structure
            text = template.get("example", plan.topic)

        # Add hashtags if they fit
        hashtags_text = " ".join(f"#{tag}" for tag in plan.hashtags[:3])

        # Check if we can fit hashtags within 280 chars
        if len(text) + len(hashtags_text) + 1 <= self.MAX_TWEET_LENGTH:
            text = f"{text} {hashtags_text}"
        elif len(text) > self.MAX_TWEET_LENGTH:
            # Truncate if too long
            available_space = self.MAX_TWEET_LENGTH - len(hashtags_text) - 4  # -4 for " ..."
            text = text[:available_space] + "..."
            if hashtags_text:
                text = f"{text} {hashtags_text}"

        return text.strip()

    def _generate_image_prompt(self, plan: PostPlan, text: str) -> str:
        """
        Generate an image prompt based on content.

        Args:
            plan: PostPlan with category and topic
            text: Generated post text

        Returns:
            Image generation prompt string
        """
        # Base style for crypto/web3 content
        base_style = "modern, professional, crypto themed, vibrant colors"

        # Category-specific visual styles
        category_styles = {
            "market_analysis": f"financial chart, {base_style}, data visualization",
            "educational": f"infographic style, {base_style}, clean layout",
            "news": f"breaking news style, {base_style}, bold typography",
            "tips": f"minimalist design, {base_style}, icon-based",
            "opinion": f"bold statement, {base_style}, striking visuals",
            "thread": f"thread visualization, {base_style}, numbered layout",
            "meme": f"meme style, {base_style}, humorous, relatable"
        }

        style = category_styles.get(plan.category, base_style)

        # Build prompt
        prompt = f"{plan.topic}, {style}, 1024x1024, high quality, digital art"

        return prompt

    def generate_batch(self, plans: List[PostPlan]) -> List[GeneratedPost]:
        """
        Generate multiple posts from a list of PostPlans.

        Args:
            plans: List of PostPlan objects

        Returns:
            List of GeneratedPost objects
        """
        posts = []
        for plan in plans:
            try:
                post = self.generate_post(plan)
                posts.append(post)
            except Exception as e:
                logger.error(f"Error generating post for plan {plan}: {e}")
                continue

        logger.info(f"Generated {len(posts)} posts from {len(plans)} plans")
        return posts
