"""Deterministic simulated data for the B3 demo.

All records are clearly marked with data_source="模拟数据（B3演示）" and are NOT real
university data. Running the script repeatedly does not duplicate records.
"""
import argparse
import json
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .config import DEFAULT_ADVISOR_WEIGHTS, DEFAULT_CANDIDATE_WEIGHTS
from .database import Base, SessionLocal, engine
from .models import (
    AdvisorMatchResult,
    AdvisorMatchTask,
    AuditLog,
    CandidateEvaluation,
    CandidateProfile,
    ImportBatch,
    ImportRowError,
    JobPosition,
    PromotionBatch,
    PromotionMaterial,
    PromotionRequirement,
    ProjectMember,
    ResearchOutput,
    ResearchProject,
    ServiceRecord,
    StudentProfile,
    SystemSetting,
    Teacher,
    TeachingRecord,
    User,
)
from .security import hash_password
from .services.matching import evaluate_position
from .services.promotion import gather_materials
from .utils import utcnow

DEMO_SOURCE = "模拟数据（B3演示）"

COLLEGE_DISCIPLINES = {
    "计算机学院": ["计算机科学与技术", "软件工程"],
    "电子信息学院": ["电子信息工程", "通信工程"],
    "机械工程学院": ["机械工程", "车辆工程"],
    "材料科学学院": ["材料科学与工程"],
    "经济管理学院": ["管理科学与工程", "工商管理"],
    "数学与统计学院": ["应用数学", "统计学"],
    "外国语学院": ["英语语言文学"],
    "马克思主义学院": ["马克思主义理论"],
}

TOPICS = {
    "计算机科学与技术": ["机器学习", "数据挖掘", "计算机视觉", "自然语言处理", "知识图谱", "分布式系统", "网络安全", "联邦学习"],
    "软件工程": ["软件测试", "程序分析", "软件架构", "智能软件工程", "需求工程"],
    "电子信息工程": ["信号处理", "无线通信", "集成电路设计", "雷达系统", "物联网"],
    "通信工程": ["5G通信", "光通信", "网络优化", "卫星通信"],
    "机械工程": ["智能制造", "机器人技术", "机械设计", "增材制造", "故障诊断"],
    "车辆工程": ["新能源汽车", "自动驾驶", "车辆动力学", "电池管理"],
    "材料科学与工程": ["纳米材料", "能源材料", "高分子材料", "金属材料", "材料表征"],
    "管理科学与工程": ["供应链管理", "数据驱动决策", "项目管理", "运筹优化"],
    "工商管理": ["战略管理", "创新创业", "市场营销", "组织行为"],
    "应用数学": ["偏微分方程", "数值计算", "概率统计", "优化理论"],
    "统计学": ["贝叶斯统计", "高维数据分析", "时间序列", "生物统计"],
    "英语语言文学": ["英美文学", "翻译研究", "语言学", "跨文化交际"],
    "马克思主义理论": ["思想政治教育", "马克思主义中国化", "社会思潮"],
}

SURNAMES = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")
GIVEN = list("伟芳娜敏静丽强磊军洋勇艳杰娟涛明超秀霞平刚桂英华玉兰萍红鹏辉宇浩凯晨鑫琳雪峰建国志强文博雅欣子涵思远嘉怡雨轩泽宇明哲俊杰晓东春梅海燕志远晓明旭东立新")

COURSE_NAMES = {
    "计算机科学与技术": ["数据结构", "机器学习导论", "人工智能基础", "计算机组成原理", "算法设计与分析"],
    "软件工程": ["软件工程导论", "软件测试技术", "软件体系结构", "需求分析", "项目实训"],
    "电子信息工程": ["信号与系统", "数字电路", "通信原理", "嵌入式系统", "电子设计自动化"],
    "通信工程": ["通信原理", "移动通信", "光纤通信", "信号处理", "网络协议分析"],
    "机械工程": ["机械原理", "机械设计", "控制工程基础", "智能制造技术", "工程制图"],
    "车辆工程": ["汽车构造", "车辆动力学", "新能源汽车技术", "汽车电子控制", "自动驾驶概论"],
    "材料科学与工程": ["材料科学基础", "材料力学性能", "纳米材料", "材料分析测试", "材料制备技术"],
    "管理科学与工程": ["运筹学", "项目管理", "管理信息系统", "决策分析", "供应链管理"],
    "工商管理": ["管理学原理", "战略管理", "市场营销", "组织行为学", "创新创业管理"],
    "应用数学": ["数学分析", "高等代数", "数值分析", "偏微分方程", "数学建模"],
    "统计学": ["概率论与数理统计", "应用回归分析", "时间序列分析", "多元统计", "统计计算"],
    "英语语言文学": ["高级英语", "英美文学", "翻译理论与实践", "语言学导论", "跨文化交际"],
    "马克思主义理论": ["马克思主义基本原理", "思想政治教育学", "中国近现代史纲要", "社会思潮研究", "形势与政策"],
}

AWARDS = ["校级优秀教学奖", "省级科技进步奖", "校级科研成果一等奖", "优秀指导教师", "教学成果二等奖", "青年科技奖"]
ACADEMIC_POSTS = ["中国计算机学会会员", "省人工智能学会理事", "专业委员会委员", "期刊编委", "行业协会专家"]
SOCIAL_SERVICES = ["企业技术顾问", "科普讲座主讲", "产学研合作项目专家", "社区技术服务", "标准评审专家"]

STUDENT_INTERESTS = [
    ("计算机科学与技术", "机器学习与数据挖掘", "深度学习、图神经网络、推荐系统", "希望参与真实工业级算法项目，有较强编程基础"),
    ("软件工程", "智能软件测试", "自动化测试、缺陷预测、程序分析", "希望提升工程实践能力并参与开源项目"),
    ("电子信息工程", "智能信号处理", "雷达信号、嵌入式系统、边缘计算", "希望获得硬件实验与算法结合的培养"),
    ("通信工程", "下一代无线通信", "5G/6G、网络切片、无线资源管理", "希望参与通信系统仿真与实验平台建设"),
    ("机械工程", "机器人感知与控制", "机器人、运动规划、机器视觉", "希望参与实验室样机开发"),
    ("车辆工程", "自动驾驶感知", "目标检测、多传感器融合、车辆控制", "希望参与实车测试与算法部署"),
    ("材料科学与工程", "新能源材料", "电池材料、纳米材料、材料计算", "希望获得材料制备与表征的系统训练"),
    ("管理科学与工程", "数据驱动决策", "供应链优化、运筹优化、机器学习", "希望参与企业合作课题"),
    ("工商管理", "创新创业管理", "商业模式、组织行为、数字化转型", "希望开展案例研究与实地调研"),
    ("应用数学", "计算数学", "数值算法、偏微分方程、科学计算", "希望参与跨学科建模项目"),
    ("统计学", "高维数据分析", "贝叶斯方法、统计学习、生物统计", "希望参与真实数据分析课题"),
    ("英语语言文学", "翻译与跨文化研究", "翻译理论、语料库、跨文化交际", "希望参与翻译实践与语料库建设"),
    ("马克思主义理论", "思想政治教育", "青年价值观、网络思政、社会思潮", "希望参与调研与课程建设"),
]


def _rng():
    return random.Random(20251025)


def _seed_users(db: Session):
    if db.query(User).count():
        return
    db.add_all([
        User(username="admin", password_hash=hash_password("admin123"),
             display_name="系统管理员", role="admin"),
        User(username="manager", password_hash=hash_password("manager123"),
             display_name="人事业务员", role="manager"),
        User(username="viewer", password_hash=hash_password("viewer123"),
             display_name="学院只读用户", role="viewer"),
    ])
    db.commit()


def _settings(db: Session):
    defaults = {
        "advisor_weights": json.dumps(DEFAULT_ADVISOR_WEIGHTS),
        "candidate_weights": json.dumps(DEFAULT_CANDIDATE_WEIGHTS),
    }
    for key, value in defaults.items():
        if not db.query(SystemSetting).filter(SystemSetting.key == key).first():
            db.add(SystemSetting(key=key, value=value, description="默认评分权重（可在系统设置调整）"))
    db.commit()


def _talent_plan(db: Session, teachers: list[Teacher]):
    if db.query(SystemSetting).filter(SystemSetting.key == "talent_plan").first():
        return
    counts = {}
    for t in teachers:
        counts[(t.college, t.discipline)] = counts.get((t.college, t.discipline), 0) + 1
    plan = []
    for idx, ((college, discipline), count) in enumerate(sorted(counts.items())):
        delta = [3, 2, 0, -1, 2, 1, -2, 3, 1, 0, 2, 1, 0][idx % 13]
        plan.append({
            "college": college,
            "discipline": discipline,
            "target_count": max(1, count + delta),
            "note": "演示规划，管理员可在系统设置中修改，非真实高校规划",
        })
    db.add(SystemSetting(
        key="talent_plan", value=json.dumps(plan, ensure_ascii=False),
        description="管理员配置的人才规划目标（用于人才缺口分析）",
    ))
    db.commit()


def _seed_teachers(db: Session) -> list[Teacher]:
    rng = _rng()
    teachers = []
    used_names = set()
    idx = 1
    college_items = []
    for college, disciplines in COLLEGE_DISCIPLINES.items():
        college_items.extend((college, discipline) for discipline in disciplines)
    while idx <= 100:
        college, discipline = college_items[(idx - 1) % len(college_items)]
        while True:
            name = rng.choice(SURNAMES) + rng.choice(GIVEN)
            if name not in used_names:
                used_names.add(name)
                break
        hire_year = rng.randint(2004, 2024)
        if hire_year <= 2010:
            title = rng.choices(["教授", "副教授"], weights=[5, 5])[0]
        elif hire_year <= 2016:
            title = rng.choices(["教授", "副教授", "讲师"], weights=[2, 5, 3])[0]
        elif hire_year <= 2020:
            title = rng.choices(["副教授", "讲师"], weights=[3, 7])[0]
        else:
            title = rng.choices(["讲师", "助教"], weights=[8, 2])[0]
        degree = rng.choices(["博士", "硕士", "学士"], weights=[7, 2.5, 0.5])[0]
        if degree != "博士" and title == "教授":
            degree = "博士"
        topics = rng.sample(TOPICS[discipline], k=min(2, len(TOPICS[discipline])))
        birth_year = rng.randint(1966, 1994)
        status = "active"
        if idx in (37, 68, 89):
            status = "on_leave"
        elif idx in (55, 97):
            status = "retired"
        advisor_qualified = degree == "博士" and title in ("教授", "副教授", "讲师") and rng.random() < 0.58
        capacity = rng.randint(2, 8) if advisor_qualified else 0
        enrollment = "closed"
        current = 0
        if advisor_qualified:
            enrollment = rng.choices(["open", "full", "closed"], weights=[7, 2, 1])[0]
            current = rng.randint(0, max(0, capacity - 1)) if enrollment == "open" else capacity
        teacher = Teacher(
            teacher_no=f"B3T{idx:04d}",
            name=name,
            gender=rng.choices(["男", "女"], weights=[6, 4])[0],
            birth_year=birth_year,
            college=college,
            department=f"{discipline}系",
            discipline=discipline,
            degree=degree,
            title=title,
            position="系主任" if rng.random() < 0.04 else "专任教师",
            hire_date=date(hire_year, rng.randint(1, 12), rng.randint(1, 28)),
            research_direction="与".join(topics) + rng.choice(["研究", "及应用", "与交叉研究"]),
            bio=f"长期从事{'、'.join(topics)}方向的教学科研工作，参与学院学科建设与人才培养。",
            skills="、".join(topics + ["科研项目管理", "学术写作", "研究生指导"]),
            research_keywords="、".join(topics + [rng.choice(["人工智能", "交叉学科", "工程实践", "理论创新"])]),
            status=status,
            advisor_qualified=advisor_qualified,
            enrollment_status=enrollment,
            capacity=capacity,
            current_students=current,
            phone=f"138{rng.randint(10000000, 99999999)}",
            email=f"b3.demo.t{idx:04d}@example.edu.cn",
            data_source=DEMO_SOURCE,
            verification_status="pending" if idx in (12, 46, 73) else "verified",
        )
        teachers.append(teacher)
        db.add(teacher)
        idx += 1
    db.flush()

    # guarantee at least two open advisors in every discipline
    by_discipline = {}
    for t in teachers:
        by_discipline.setdefault(t.discipline, []).append(t)
    for discipline, rows in by_discipline.items():
        open_advisors = [t for t in rows if t.advisor_qualified and t.enrollment_status == "open"]
        if len(open_advisors) < 2:
            for t in rows:
                if len(open_advisors) >= 2:
                    break
                if t.advisor_qualified:
                    continue
                t.advisor_qualified = True
                t.capacity = max(t.capacity, 4)
                t.current_students = min(t.current_students, 2)
                t.enrollment_status = "open"
                open_advisors.append(t)
    db.commit()
    return teachers


def _seed_research(db: Session, teachers: list[Teacher], rng: random.Random):
    prefix_words = ["基于深度学习的", "面向复杂场景的", "可解释的", "多模态", "高效的", "面向工业应用的", "融合知识图谱的"]
    suffix_words = ["方法研究", "关键技术研究", "系统设计与实现", "应用研究", "模型构建与验证"]
    venues = ["《计算机学报》", "《软件学报》", "《自动化学报》", "IEEE Transactions", "ACM Conference", "《管理科学学报》", "《材料学报》", "《外语教学与研究》"]
    levels = ["SCI一区", "SCI二区", "SCI三区", "EI", "CSSCI", "中文核心", "普通"]
    outputs = []
    output_index = 1
    for t in teachers:
        base = {"教授": 8, "副教授": 5, "讲师": 3, "助教": 1}[t.title]
        count = max(0, int(rng.gauss(base, 3)))
        topics = split_topics(t.research_direction)
        for _ in range(count):
            year = rng.randint(2017, 2025)
            topic = rng.choice(topics) if topics else "交叉学科"
            output_type = rng.choices(["paper", "patent", "book", "report"], weights=[8, 1.2, 0.4, 0.4])[0]
            title = f"{rng.choice(prefix_words)}{topic}{rng.choice(suffix_words)}"
            if output_type == "patent":
                title = f"一种{topic}相关的{'装置' if rng.random() < 0.5 else '系统'}及方法"
            elif output_type == "book":
                title = f"{topic}：理论与实践"
            elif output_type == "report":
                title = f"{topic}发展研究报告"
            outputs.append(ResearchOutput(
                teacher_id=t.id,
                output_type=output_type,
                title=title,
                venue=rng.choice(venues),
                publish_date=date(year, rng.randint(1, 12), rng.randint(1, 28)),
                level=rng.choice(levels),
                authors=f"{t.name}、合作者A、合作者B",
                doi=f"10.9999/b3.{output_index:05d}",
                data_source=DEMO_SOURCE + ("/待核验" if rng.random() < 0.04 else ""),
            ))
            output_index += 1
    db.add_all(outputs)

    project_topics = [t for rows in TOPICS.values() for t in rows]
    projects = []
    for pidx in range(1, 61):
        principal = rng.choice(teachers)
        topic = rng.choice(project_topics)
        start_year = rng.randint(2018, 2025)
        start = date(start_year, rng.randint(1, 12), 1)
        end = date(start_year + rng.randint(1, 3), 12, 31)
        project = ResearchProject(
            project_no=f"B3P{pidx:04d}",
            name=f"{topic}关键技术研究及{'应用示范' if rng.random() < 0.5 else '平台建设'}",
            level=rng.choice(["国家级", "省部级", "厅局级", "横向课题"]),
            funding=round(rng.uniform(10, 220), 1),
            start_date=start,
            end_date=end,
            principal_teacher_id=principal.id,
            status=rng.choices(["ongoing", "completed"], weights=[4, 6])[0],
            data_source=DEMO_SOURCE,
        )
        projects.append(project)
        db.add(project)
        db.flush()
        db.add(ProjectMember(project_id=project.id, teacher_id=principal.id, role="主持人", contribution_pct=60))
        for member in rng.sample([x for x in teachers if x.id != principal.id], k=rng.randint(1, 4)):
            db.add(ProjectMember(
                project_id=project.id, teacher_id=member.id, role="参与人",
                contribution_pct=round(rng.uniform(5, 40), 1),
            ))

    teaching = []
    for t in teachers:
        courses = COURSE_NAMES.get(t.discipline, ["专业导论"])
        for _ in range(rng.randint(1, 5)):
            year = rng.randint(2021, 2025)
            hours = rng.choice([24, 32, 48, 64])
            achievement = None
            if rng.random() < 0.18:
                achievement = f"{year}年{rng.choice(['校级教学成果二等奖', '课程思政示范课程', '优秀教材奖', '教学创新大赛三等奖'])}"
            teaching.append(TeachingRecord(
                teacher_id=t.id,
                course_name=rng.choice(courses),
                academic_year=f"{year}-{year + 1}",
                semester=rng.choice(["第一学期", "第二学期"]),
                hours=hours,
                student_count=rng.randint(20, 120),
                teaching_level=rng.choice(["本科", "研究生"]),
                evaluation_score=round(rng.uniform(82, 98), 1),
                achievement=achievement,
                data_source=DEMO_SOURCE,
            ))
    db.add_all(teaching)

    services = []
    for t in teachers:
        for _ in range(rng.randint(0, 3)):
            service_type = rng.choices(["award", "academic_post", "social_service"], weights=[4, 3, 3])[0]
            year = rng.randint(2018, 2025)
            if service_type == "award":
                name = rng.choice(AWARDS)
            elif service_type == "academic_post":
                name = rng.choice(ACADEMIC_POSTS)
            else:
                name = rng.choice(SOCIAL_SERVICES)
            services.append(ServiceRecord(
                teacher_id=t.id,
                service_type=service_type,
                name=name,
                organization=f"{t.college}或校外合作单位（演示）",
                role="负责人" if rng.random() < 0.3 else "成员",
                start_date=date(year, rng.randint(1, 12), 1),
                end_date=date(year, 12, 31),
                description=f"演示记录：{name}",
                data_source=DEMO_SOURCE,
            ))
    db.add_all(services)
    db.commit()


def split_topics(text: str | None) -> list[str]:
    if not text:
        return []
    for sep in ["与交叉研究", "及应用", "与", "研究"]:
        text = text.replace(sep, "、")
    return [p for p in text.replace("、", ",").split(",") if p]


def _seed_students(db: Session, rng: random.Random):
    students = []
    for idx in range(1, 21):
        discipline, direction, keywords, needs = STUDENT_INTERESTS[(idx - 1) % len(STUDENT_INTERESTS)]
        students.append(StudentProfile(
            student_no=f"B3S{idx:04d}",
            name=f"学生{rng.choice(SURNAMES)}{rng.choice(GIVEN)}",
            major=discipline,
            discipline=discipline,
            research_interest=direction,
            keywords=keywords,
            desired_direction=direction + "方向",
            training_needs=needs,
            degree_goal=rng.choice(["学术型硕士", "专业型硕士", "博士"]),
            other_conditions=rng.choice(["希望有企业联合培养机会", "希望参与国家级项目", "希望每周有固定组会", "暂无其他条件"]),
        ))
    db.add_all(students)
    db.commit()
    return students


def _seed_promotion(db: Session, teachers: list[Teacher], manager: User):
    batches_def = [
        {
            "name": "2026年度计算机学院副教授申报（示例批次）",
            "year": 2026, "title_type": "副教授", "college": "计算机学院",
            "deadline": date(2026, 11, 30), "status": "open",
            "requirements": [
                {"category": "paper", "name": "代表性论文/著作", "min_count": 3,
                 "requirement_desc": "示例配置：近5年代表性成果不少于3项；非真实高校统一政策。", "keywords": "", "window_years": 5},
                {"category": "project", "name": "主持科研项目", "min_count": 1,
                 "requirement_desc": "示例配置：近5年主持项目不少于1项。", "principal_only": True, "window_years": 5},
                {"category": "teaching", "name": "主讲课程", "min_count": 2,
                 "requirement_desc": "示例配置：近5年主讲课程不少于2门次。", "window_years": 5},
                {"category": "award", "name": "获奖或教学成果", "min_count": 1,
                 "requirement_desc": "示例配置：近5年获奖或教学成果不少于1项（非必填）。", "mandatory": False, "window_years": 5},
                {"category": "service", "name": "学术任职或社会服务", "min_count": 1,
                 "requirement_desc": "示例配置：近5年学术任职或社会服务不少于1项（非必填）。", "mandatory": False, "window_years": 5},
            ],
        },
        {
            "name": "2026年度全校教授申报（示例批次）",
            "year": 2026, "title_type": "教授", "college": None,
            "deadline": date(2026, 10, 31), "status": "open",
            "requirements": [
                {"category": "paper", "name": "高水平代表作", "min_count": 5,
                 "requirement_desc": "示例配置：近5年代表性成果不少于5项。", "window_years": 5},
                {"category": "project", "name": "主持省部级以上项目", "min_count": 2,
                 "requirement_desc": "示例配置：近5年主持项目不少于2项。", "principal_only": True, "window_years": 5},
                {"category": "award", "name": "省部级及以上获奖", "min_count": 1,
                 "requirement_desc": "示例配置：近5年获奖不少于1项。", "window_years": 5},
                {"category": "teaching", "name": "研究生课程", "min_count": 2,
                 "requirement_desc": "示例配置：近5年主讲课程不少于2门次。", "window_years": 5},
            ],
        },
        {
            "name": "2025年度材料科学学院副教授申报（已结束示例）",
            "year": 2025, "title_type": "副教授", "college": "材料科学学院",
            "deadline": date(2025, 9, 30), "status": "completed",
            "requirements": [
                {"category": "paper", "name": "代表性论文", "min_count": 3,
                 "requirement_desc": "示例配置：近5年代表性成果不少于3项。", "window_years": 5},
                {"category": "project", "name": "主持项目", "min_count": 1,
                 "requirement_desc": "示例配置：近5年主持项目不少于1项。", "principal_only": True, "window_years": 5},
                {"category": "award", "name": "获奖", "min_count": 1,
                 "requirement_desc": "示例配置：近5年获奖不少于1项。", "window_years": 5},
            ],
        },
    ]
    batches = []
    for item in batches_def:
        reqs = item.pop("requirements")
        batch = PromotionBatch(**item)
        db.add(batch)
        db.flush()
        for req in reqs:
            db.add(PromotionRequirement(
                batch_id=batch.id,
                category=req["category"],
                name=req["name"],
                requirement_desc=req.get("requirement_desc"),
                min_count=req.get("min_count", 1),
                mandatory=req.get("mandatory", True),
                keywords=req.get("keywords"),
                window_years=req.get("window_years", 5),
                principal_only=req.get("principal_only", False),
            ))
        db.flush()
        batches.append(batch)
    db.commit()

    cs_teachers = [t for t in teachers if t.college == "计算机学院"][:5]
    for teacher in cs_teachers:
        gather_materials(db, batches[0], teacher)
    for teacher in [t for t in teachers if t.college == "计算机学院" and t.title == "副教授"][:3]:
        gather_materials(db, batches[1], teacher)
    for teacher in [t for t in teachers if t.college == "材料科学学院"][:5]:
        gather_materials(db, batches[2], teacher)

    # some manual decisions for demo
    materials = db.query(PromotionMaterial).filter(PromotionMaterial.status == "matched").limit(6).all()
    for m in materials[:3]:
        m.status = "confirmed"
        m.note = "演示：业务人员已核对原始材料"
        m.updated_by = manager.username
    for m in materials[3:6]:
        m.status = "pending_verification"
        m.note = "演示：来源数据需要人工核验"
        m.updated_by = manager.username
    db.commit()
    return batches


def _seed_recruitment(db: Session, teachers: list[Teacher], rng: random.Random):
    positions_def = [
        {
            "name": "人工智能与机器学习方向青年教授/副教授", "college": "计算机学院",
            "discipline": "计算机科学与技术", "research_direction": "机器学习、数据挖掘、人工智能",
            "required_degree": "博士", "min_outputs": 4,
            "research_topics": "深度学习、图神经网络、推荐系统、联邦学习",
            "requirements_desc": "具有博士学位，近五年高水平论文不少于4篇，能够承担人工智能方向研究生课程。",
        },
        {
            "name": "软件工程方向教学科研岗", "college": "计算机学院", "discipline": "软件工程",
            "research_direction": "软件测试、程序分析、智能软件工程",
            "required_degree": "博士", "min_outputs": 3,
            "research_topics": "自动化测试、缺陷预测、软件架构",
            "requirements_desc": "具有博士学位，具备软件工程科研与教学能力，成果不少于3项。",
        },
        {
            "name": "新能源材料方向青年人才", "college": "材料科学学院", "discipline": "材料科学与工程",
            "research_direction": "能源材料、纳米材料",
            "required_degree": "博士", "min_outputs": 3,
            "research_topics": "电池材料、材料表征、材料计算",
            "requirements_desc": "具有博士学位，在能源材料方向有代表性成果。",
        },
        {
            "name": "智能车辆与自动驾驶研究员", "college": "机械工程学院", "discipline": "车辆工程",
            "research_direction": "自动驾驶、车辆动力学、多传感器融合",
            "required_degree": "博士", "min_outputs": 2,
            "research_topics": "目标检测、路径规划、车辆控制",
            "requirements_desc": "具有博士学位或同等工程经历，成果不少于2项。",
        },
        {
            "name": "数字经济与供应链管理教师", "college": "经济管理学院", "discipline": "管理科学与工程",
            "research_direction": "供应链管理、数据驱动决策、运筹优化",
            "required_degree": "博士", "min_outputs": 2,
            "research_topics": "供应链金融、智能决策、平台运营",
            "requirements_desc": "博士学位，具备数据驱动管理研究能力。",
        },
        {
            "name": "应用数学方向讲师/副教授", "college": "数学与统计学院", "discipline": "应用数学",
            "research_direction": "数值计算、偏微分方程、科学计算",
            "required_degree": "硕士", "min_outputs": 1,
            "research_topics": "数值算法、科学计算、数学建模",
            "requirements_desc": "硕士及以上学历，具备数学建模与教学能力。",
        },
    ]
    positions = []
    for idx, item in enumerate(positions_def, start=1):
        position = JobPosition(
            **item,
            weights=json.dumps(DEFAULT_CANDIDATE_WEIGHTS),
            status="open",
        )
        db.add(position)
        positions.append(position)
    db.commit()

    candidate_names = ["陈思远", "林雨欣", "张启航", "王若楠", "周子墨", "赵一鸣", "孙嘉禾", "吴梓涵",
                       "郑博文", "刘书瑶", "黄俊熙", "徐佳宁", "胡天宇", "朱可欣", "高远航", "何芷晴",
                       "罗辰逸", "梁诗涵"]
    name_idx = 0
    for p_idx, position in enumerate(positions):
        for j in range(3):
            name = candidate_names[name_idx]
            name_idx += 1
            degree = rng.choices(["博士", "硕士", "学士"], weights=[7, 2.5, 0.5])[0]
            outputs = rng.randint(0, 12)
            if j == 0:
                outputs = max(outputs, position.min_outputs + 2)
                degree = "博士" if position.required_degree == "博士" else degree
            if j == 2:
                outputs = max(0, position.min_outputs - 2)
            topics = split_topics(position.research_direction) or [position.discipline]
            keywords = "、".join(rng.sample(TOPICS.get(position.discipline, topics), k=min(2, len(TOPICS.get(position.discipline, topics)))))
            candidate = CandidateProfile(
                name=name,
                position_id=position.id,
                degree=degree,
                graduate_school=rng.choice(["示范大学", "理工大学", "科技大学", "海内外知名高校（演示）"]),
                major=position.discipline,
                research_direction=f"{rng.choice(topics)}与{keywords}",
                keywords=keywords,
                outputs_count=outputs,
                projects_count=rng.randint(0, 6),
                teaching_years=round(rng.uniform(0, 8), 1),
                output_evidence=f"演示档案：近五年发表/授权成果 {outputs} 项，其中第一作者 {max(0, outputs - 2)} 项",
                project_evidence=f"演示档案：参与科研项目 {rng.randint(0, 4)} 项，主持 {rng.randint(0, 2)} 项",
                teaching_evidence=f"演示档案：承担课程教学 {round(rng.uniform(0, 5), 1)} 年",
                source=DEMO_SOURCE,
                unverified_fields="主持项目数量待核验" if j == 1 else None,
            )
            db.add(candidate)
    db.commit()

    for position in positions:
        evaluate_position(db, position)

    evals = db.query(CandidateEvaluation).filter(CandidateEvaluation.hard_pass.is_(True)).limit(3).all()
    for ev in evals[:2]:
        ev.review_status = "shortlisted"
        ev.reviewer = "manager"
        ev.review_note = "演示：进入下一轮面试"
    for ev in evals[2:3]:
        ev.review_status = "reviewed"
        ev.reviewer = "manager"
        ev.review_note = "演示：材料已审阅，建议补充成果证明"
    db.commit()
    return positions


def _seed_audit(db: Session):
    if db.query(AuditLog).count():
        return
    db.add_all([
        AuditLog(username="system", action="seed", resource_type="system", detail="初始化 B3 演示数据"),
        AuditLog(username="admin", action="login", resource_type="auth", detail="演示登录记录"),
        AuditLog(username="manager", action="update", resource_type="promotion_material", detail="演示评审记录"),
    ])
    db.commit()


def seed_all(db: Session, force: bool = False) -> dict:
    if force:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db.expire_all()
    _seed_users(db)
    if db.query(Teacher).count() and not force:
        _settings(db)
        return {
            "skipped": True,
            "message": "检测到已有教师数据，跳过初始化（使用 --force 可重建演示数据）",
            "teachers": db.query(Teacher).count(),
        }

    rng = _rng()
    _settings(db)
    teachers = _seed_teachers(db)
    _seed_research(db, teachers, rng)
    _seed_students(db, rng)
    manager = db.query(User).filter(User.username == "manager").first()
    _seed_promotion(db, teachers, manager)
    _seed_recruitment(db, teachers, rng)
    _talent_plan(db, teachers)
    _seed_audit(db)
    return {
        "skipped": False,
        "message": "演示数据初始化完成",
        "teachers": db.query(Teacher).count(),
        "outputs": db.query(ResearchOutput).count(),
        "projects": db.query(ResearchProject).count(),
        "teaching": db.query(TeachingRecord).count(),
        "services": db.query(ServiceRecord).count(),
        "students": db.query(StudentProfile).count(),
        "positions": db.query(JobPosition).count(),
        "candidates": db.query(CandidateProfile).count(),
        "promotion_materials": db.query(PromotionMaterial).count(),
        "source": DEMO_SOURCE,
    }


def main():
    parser = argparse.ArgumentParser(description="Initialize B3 demo data")
    parser.add_argument("--force", action="store_true", help="drop and rebuild all tables")
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_all(db, force=args.force)
        for key, value in result.items():
            print(f"{key}: {value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
