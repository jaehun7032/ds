from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_pymongo import PyMongo
from bson import ObjectId
from datetime import datetime
from pymongo.errors import PyMongoError
from app.utils.helpers import logger, safe_object_id, handle_db_error

cards_bp = Blueprint('cards', __name__)

def init_cards(app):
    global mongo
    mongo = PyMongo(app)

@cards_bp.route("/projects/all/cards", methods=["GET"])
@login_required
def get_all_cards():
    projects = mongo.db.projects.find({"members": ObjectId(current_user.get_id())})
    project_ids = [project["_id"] for project in projects]
    
    cards = list(mongo.db.cards.find({"project_id": {"$in": project_ids}}).sort("order", 1))
    logger.info(f"Retrieved {len(cards)} cards for user {current_user.get_id()}")
    return jsonify({
        "cards": [{
            "id": str(card["_id"]),
            "title": card["title"],
            "description": card["description"],
            "status": card["status"],
            "project_id": str(card["project_id"]),
            "created_by": str(card["created_by"]),
            "created_at": card["created_at"].isoformat(),
            "order": card.get("order", 0)
        } for card in cards]
    }), 200

@cards_bp.route("/projects/all/cards/counts", methods=["GET"])
@login_required
def get_card_counts():
    projects = mongo.db.projects.find({"members": ObjectId(current_user.get_id())})
    counts = {}
    
    for project in projects:
        project_id = str(project["_id"])
        count = mongo.db.cards.count_documents({"project_id": project["_id"]})
        counts[project_id] = count
    
    logger.info(f"Retrieved card counts for user {current_user.get_id()}")
    return jsonify({"counts": counts}), 200

@cards_bp.route("/projects/<project_id>/cards/move", methods=["POST"])
@login_required
def move_card(project_id):
    data = request.get_json()
    card_id = data.get("cardId")
    target_project_id = data.get("projectId")
    order = data.get("order", [])

    oid = safe_object_id(project_id)
    card_oid = safe_object_id(card_id)
    target_oid = safe_object_id(target_project_id)
    if not all([oid, card_oid, target_oid]):
        return jsonify({"message": "유효하지 않은 ID입니다."}), 400

    project = mongo.db.projects.find_one({"_id": target_oid})
    if not project:
        logger.error(f"Target project not found: {target_project_id}")
        return jsonify({"message": "대상 프로젝트를 찾을 수 없습니다."}), 404

    if ObjectId(current_user.get_id()) not in project.get("members", []):
        logger.error(f"User {current_user.get_id()} not a member of project {target_project_id}")
        return jsonify({"message": "권한이 없습니다."}), 403

    try:
        # 카드 이동
        card = mongo.db.cards.find_one({"_id": card_oid})
        if not card:
            logger.error(f"Card {card_id} not found")
            return jsonify({"message": "카드를 찾을 수 없습니다."}), 404

        mongo.db.cards.update_one(
            {"_id": card_oid},
            {"$set": {"project_id": target_oid}}
        )

        # 순서 업데이트
        order_oids = [safe_object_id(cid) for cid in order]
        if None in order_oids:
            return jsonify({"error": "유효하지 않은 카드 ID입니다."}), 400

        for index, cid in enumerate(order_oids):
            card_check = mongo.db.cards.find_one({"_id": cid, "project_id": target_oid})
            if not card_check:
                logger.error(f"Card {cid} not found in project {target_project_id}")
                return jsonify({"error": f"카드 {cid}를 프로젝트에서 찾을 수 없습니다."}), 404

            mongo.db.cards.update_one(
                {"_id": cid, "project_id": target_oid},
                {"$set": {"order": index}}
            )

        logger.info(f"Card {card_id} moved to project {target_project_id} and order updated")
        return jsonify({"message": "카드가 이동되고 순서가 업데이트되었습니다."}), 200
    except PyMongoError as e:
        return handle_db_error(e)

@cards_bp.route("/projects/<project_id>/cards", methods=["POST"])
@login_required
def create_card(project_id):
    data = request.get_json()
    if not data or "title" not in data:
        logger.error("Missing card title in request")
        return jsonify({"message": "카드 제목이 필요합니다."}), 400

    oid = safe_object_id(project_id)
    if not oid:
        return jsonify({"message": "유효하지 않은 프로젝트 ID입니다."}), 400

    project = mongo.db.projects.find_one({"_id": oid})
    if not project:
        logger.error(f"Project not found: {project_id}")
        return jsonify({"message": "프로젝트를 찾을 수 없습니다."}), 404

    if ObjectId(current_user.get_id()) not in project.get("members", []):
        logger.error(f"User {current_user.get_id()} not a member of project {project_id}")
        return jsonify({"message": "권한이 없습니다."}), 403

    try:
        max_order_doc = mongo.db.cards.find({"project_id": oid}).sort("order", -1).limit(1)
        max_order_doc = next(max_order_doc, None)
        max_order = max_order_doc["order"] + 1 if max_order_doc else 0

        new_card = {
            "project_id": oid,
            "title": data["title"],
            "description": data.get("description", ""),
            "created_by": ObjectId(current_user.get_id()),
            "created_at": datetime.utcnow(),
            "status": "todo",
            "order": max_order
        }

        result = mongo.db.cards.insert_one(new_card)
        logger.info(f"Created card: {result.inserted_id} in project {project_id}")
        return jsonify({
            "id": str(result.inserted_id),
            "title": new_card["title"],
            "description": new_card["description"],
            "status": new_card["status"],
            "project_id": str(new_card["project_id"]),
            "order": new_card["order"]
        }), 201
    except Exception as e:
        return handle_db_error(e)

@cards_bp.route("/projects/<project_id>/cards/<card_id>", methods=["DELETE"])
@login_required
def delete_card(project_id, card_id):
    oid = safe_object_id(project_id)
    card_oid = safe_object_id(card_id)
    if not all([oid, card_oid]):
        return jsonify({"message": "유효하지 않은 프로젝트 또는 카드 ID입니다."}), 400

    project = mongo.db.projects.find_one({"_id": oid})
    if not project:
        logger.error(f"Project not found: {project_id}")
        return jsonify({"message": "프로젝트를 찾을 수 없습니다."}), 404

    if ObjectId(current_user.get_id()) not in project.get("members", []):
        logger.error(f"User {current_user.get_id()} not a member of project {project_id}")
        return jsonify({"message": "권한이 없습니다."}), 403

    card = mongo.db.cards.find_one({"_id": card_oid, "project_id": oid})
    if not card:
        logger.error(f"Card not found: {card_id}")
        return jsonify({"message": "카드를 찾을 수 없습니다."}), 404

    mongo.db.cards.delete_one({"_id": card_oid})
    logger.info(f"Deleted card: {card_id} from project {project_id}")
    return jsonify({"message": "카드가 삭제되었습니다."}), 200

@cards_bp.route("/projects/<project_id>/cards", methods=["GET"])
@login_required
def get_project_cards(project_id):
    oid = safe_object_id(project_id)
    if not oid:
        return jsonify({"message": "유효하지 않은 프로젝트 ID입니다."}), 400

    project = mongo.db.projects.find_one({"_id": oid})
    if not project:
        logger.error(f"Project not found: {project_id}")
        return jsonify({"message": "프로젝트를 찾을 수 없습니다."}), 404

    if ObjectId(current_user.get_id()) not in project.get("members", []):
        logger.error(f"User {current_user.get_id()} not a member of project {project_id}")
        return jsonify({"message": "권한이 없습니다."}), 403

    cards = list(mongo.db.cards.find({"project_id": oid}).sort("order", 1))
    logger.info(f"Retrieved {len(cards)} cards for project {project_id}")
    return jsonify({
        "cards": [{
            "id": str(card["_id"]),
            "title": card["title"],
            "description": card["description"],
            "status": card["status"],
            "project_id": str(card["project_id"]),
            "created_by": str(card["created_by"]),
            "created_at": card["created_at"].isoformat(),
            "order": card.get("order", 0)
        } for card in cards]
    }), 200

@cards_bp.route("/projects/<project_id>/cards/<card_id>/status", methods=["PUT"])
@login_required
def update_card_status(project_id, card_id):
    data = request.get_json()
    if not data or "status" not in data:
        logger.error("Missing status in request")
        return jsonify({"message": "상태 정보가 필요합니다."}), 400

    oid = safe_object_id(project_id)
    card_oid = safe_object_id(card_id)
    if not all([oid, card_oid]):
        return jsonify({"message": "유효하지 않은 프로젝트 또는 카드 ID입니다."}), 400

    project = mongo.db.projects.find_one({"_id": oid})
    if not project:
        logger.error(f"Project not found: {project_id}")
        return jsonify({"message": "프로젝트를 찾을 수 없습니다."}), 404

    if ObjectId(current_user.get_id()) not in project.get("members", []):
        logger.error(f"User {current_user.get_id()} not a member of project {project_id}")
        return jsonify({"message": "권한이 없습니다."}), 403

    card = mongo.db.cards.find_one({"_id": card_oid, "project_id": oid})
    if not card:
        logger.error(f"Card not found: {card_id}")
        return jsonify({"message": "카드를 찾을 수 없습니다."}), 404

    mongo.db.cards.update_one(
        {"_id": card_oid},
        {"$set": {"status": data["status"]}}
    )
    logger.info(f"Updated status of card {card_id} to {data['status']}")
    return jsonify({"message": "카드 상태가 업데이트되었습니다."}), 200

@cards_bp.route('/projects/<project_id>/cards/reorder', methods=['POST'])
@login_required
def reorder_cards(project_id):
    oid = safe_object_id(project_id)
    if not oid:
        return jsonify({'error': '유효하지 않은 프로젝트 ID입니다.'}), 400

    project = mongo.db.projects.find_one({"_id": oid})
    if not project:
        logger.error(f"Project not found: {project_id}")
        return jsonify({'error': '프로젝트를 찾을 수 없습니다.'}), 404

    if ObjectId(current_user.get_id()) not in project.get("members", []):
        logger.error(f"User {current_user.get_id()} not a member of project {project_id}")
        return jsonify({"error": "권한이 없습니다."}), 403

    data = request.get_json()
    order = data.get("order")
    if not isinstance(order, list):
        logger.error(f"Invalid order format: {order}")
        return jsonify({'error': 'Order must be a list of card IDs'}), 400

    order_oids = [safe_object_id(card_id) for card_id in order]
    if None in order_oids:
        return jsonify({'error': '유효하지 않은 카드 ID입니다.'}), 400

    for card_id in order_oids:
        card = mongo.db.cards.find_one({"_id": card_id, "project_id": oid})
        if not card:
            logger.error(f"Card {card_id} not found in project {project_id}")
            return jsonify({'error': f"카드 {card_id}를 찾을 수 없습니다."}), 404

    try:
        with mongo.cx.start_session() as session:
            with session.start_transaction():
                for index, card_id in enumerate(order_oids):
                    mongo.db.cards.update_one(
                        {"_id": card_id, "project_id": oid},
                        {"$set": {"order": index}},
                        session=session
                    )
    except PyMongoError as e:
        return handle_db_error(e)

    logger.info(f"Cards reordered in project {project_id}")
    return jsonify({'message': '카드 순서가 업데이트되었습니다.'}), 200

@cards_bp.route("/projects/<project_id>/cards/<card_id>", methods=["PUT"])
@login_required
def update_card(project_id, card_id):
    data = request.get_json()
    if not data or "title" not in data:
        logger.error("Missing card title in request")
        return jsonify({"message": "카드 제목이 필요합니다."}), 400

    oid = safe_object_id(project_id)
    card_oid = safe_object_id(card_id)
    if not all([oid, card_oid]):
        return jsonify({"message": "유효하지 않은 프로젝트 또는 카드 ID입니다."}), 400

    project = mongo.db.projects.find_one({"_id": oid})
    if not project:
        logger.error(f"Project not found: {project_id}")
        return jsonify({"message": "프로젝트를 찾을 수 없습니다."}), 404

    if ObjectId(current_user.get_id()) not in project.get("members", []):
        logger.error(f"User {current_user.get_id()} not a member of project {project_id}")
        return jsonify({"message": "권한이 없습니다."}), 403

    card = mongo.db.cards.find_one({"_id": card_oid, "project_id": oid})
    if not card:
        logger.error(f"Card not found: {card_id}")
        return jsonify({"message": "카드를 찾을 수 없습니다."}), 404

    update_data = {
        "title": data["title"],
        "description": data.get("description", "")
    }

    mongo.db.cards.update_one(
        {"_id": card_oid},
        {"$set": update_data}
    )
    logger.info(f"Updated card: {card_id} in project {project_id}")
    return jsonify({"message": "카드가 수정되었습니다."}), 200
