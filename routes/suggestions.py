from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from services.recommendation_service import RecommendationService
from services.security_service import user_required

suggestions_bp = Blueprint("suggestions", __name__)


@suggestions_bp.route("/suggestions")
@login_required
@user_required
def index():
    user_id = current_user.user_id
    category_filter = request.args.get("category", "").strip()

    data = RecommendationService.get_personalized_suggestions(user_id=user_id)
    all_suggestions = data["all_suggestions"]

    if category_filter:
        filtered_suggestions = [s for s in all_suggestions if s.category.lower() == category_filter.lower()]
    else:
        filtered_suggestions = all_suggestions

    return render_template(
        "suggestions/index.html",
        notes=data["notes"],
        recommended=data["recommended"],
        all_suggestions=filtered_suggestions,
        categories=data["categories"],
        selected_category=category_filter,
    )
