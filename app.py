from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import config
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_object(config)

# 修改CORS配置
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:8080"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
        "supports_credentials": True
    }
})

db = SQLAlchemy(app)

# 面包分类模型
class Category(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    breads = db.relationship('Bread', backref='category', lazy=True)

# 面包模型
class Bread(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))
    category_id = db.Column(db.String(50), db.ForeignKey('category.id'), nullable=False)
    description = db.Column(db.Text)
    ingredients = db.Column(db.JSON)
    stock = db.Column(db.Integer, default=0)
    in_stock = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 订单模型
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)  # TB20230005
    customer_name = db.Column(db.String(100), nullable=False)  # 客户姓名
    phone = db.Column(db.String(20))  # 联系电话
    address = db.Column(db.String(200))  # 配送地址
    order_date = db.Column(db.DateTime, default=datetime.utcnow)  # 下单时间
    pickup_time = db.Column(db.DateTime)  # 取餐时间
    payment_method = db.Column(db.String(20))  # 支付方式：cash, wechat, alipay, card
    status = db.Column(db.String(20), default='pending')  # 订单状态：pending, processing, completed, cancelled
    discount = db.Column(db.Float, default=0.0)  # 折扣金额
    delivery_fee = db.Column(db.Float, default=0.0)  # 配送费
    total_amount = db.Column(db.Float, nullable=False)  # 订单总金额
    notes = db.Column(db.Text)  # 订单备注
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')  # 订单项关联

# 订单项模型
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)  # 关联订单ID
    name = db.Column(db.String(100), nullable=False)  # 面包名称
    bread_type = db.Column(db.String(50))  # 面包类型：sourdough, baguette, croissant等
    price = db.Column(db.Float, nullable=False)  # 单价
    quantity = db.Column(db.Integer, nullable=False)  # 数量

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='staff')
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 财务支出模型
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    expense_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False)  # 支出类别：原料采购、人工成本、水电费用、设备维护、店铺租金、其他支出
    amount = db.Column(db.Float, nullable=False)  # 支出金额
    note = db.Column(db.String(200))  # 备注
    created_by = db.Column(db.String(50))  # 创建人
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 记录创建时间

# 初始化数据库
def init_db():
    with app.app_context():
        db.create_all()
        
        # 检查是否已有支出数据
        if Expense.query.first() is None:
            print("正在生成财务支出模拟数据...")
            
            # 支出类别和对应的备注
            expense_categories = {
                '原料采购': ['面粉采购', '糖采购', '奶油采购', '酵母采购', '水果采购', '巧克力采购', '坚果采购', '其他原料'],
                '人工成本': ['员工工资', '员工奖金', '员工培训', '社保缴纳', '临时工薪资', '加班补贴'],
                '水电费用': ['水费', '电费', '燃气费', '宽带费', '暖气费'],
                '设备维护': ['烤箱维修', '搅拌机维护', '冷柜清洗', '设备更新', '厨房设备保养', '电器维修'],
                '店铺租金': ['店铺月租', '物业费', '保证金', '场地装修'],
                '其他支出': ['清洁用品', '办公用品', '广告宣传', '包装材料', '餐具更新', '杂项支出']
            }
            
            # 创建者列表
            creators = ['admin', 'staff', 'manager', 'accountant']
            
            # 生成与订单相匹配的支出数据
            # 按月生成支出
            expenses = []
            import random
            from datetime import timedelta
            
            # 获取所有已完成订单，按月份分组
            orders_by_month = {}
            all_orders = Order.query.filter_by(status='completed').all()
            
            for order in all_orders:
                order_month = order.order_date.month
                order_year = order.order_date.year
                month_key = f"{order_year}-{order_month}"
                
                if month_key not in orders_by_month:
                    orders_by_month[month_key] = []
                
                orders_by_month[month_key].append(order)
            
            # 为每个月生成支出数据
            for month_key, month_orders in orders_by_month.items():
                year, month = map(int, month_key.split('-'))
                
                # 计算月份的起止时间
                month_start = datetime(year, month, 1)
                if month == 12:
                    month_end = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    month_end = datetime(year, month + 1, 1) - timedelta(days=1)
                
                # 计算当月总收入
                month_income = sum(order.total_amount for order in month_orders)
                
                if month_income > 0:  # 只有当月有收入时才生成支出
                    # 原料采购：约占收入的25%
                    material_expense_total = month_income * random.uniform(0.22, 0.28)
                    material_expense_count = random.randint(3, 8)  # 每月3-8次采购
                    for _ in range(material_expense_count):
                        category = '原料采购'
                        amount = material_expense_total / material_expense_count * random.uniform(0.8, 1.2)  # 添加一些随机波动
                        expense_date = month_start + timedelta(days=random.randint(0, (month_end - month_start).days))
                        note = random.choice(expense_categories[category])
                        created_by = random.choice(creators)
                        
                        expenses.append(Expense(
                            expense_date=expense_date,
                            category=category,
                            amount=round(amount, 2),
                            note=note,
                            created_by=created_by
                        ))
                    
                    # 人工成本：约占收入的15%
                    labor_expense = month_income * random.uniform(0.13, 0.17)
                    expense_date = month_end - timedelta(days=random.randint(0, 5))  # 月底发工资
                    expenses.append(Expense(
                        expense_date=expense_date,
                        category='人工成本',
                        amount=round(labor_expense, 2),
                        note='员工工资',
                        created_by='admin'
                    ))
                    
                    # 水电费用：约占收入的5%
                    utility_expense = month_income * random.uniform(0.04, 0.06)
                    expense_date = month_start + timedelta(days=random.randint(10, 20))
                    expenses.append(Expense(
                        expense_date=expense_date,
                        category='水电费用',
                        amount=round(utility_expense, 2),
                        note=random.choice(expense_categories['水电费用']),
                        created_by=random.choice(creators)
                    ))
                    
                    # 设备维护：约占收入的3%
                    if random.random() > 0.3:  # 不是每个月都有设备维护
                        equipment_expense = month_income * random.uniform(0.02, 0.04)
                        expense_date = month_start + timedelta(days=random.randint(0, (month_end - month_start).days))
                        expenses.append(Expense(
                            expense_date=expense_date,
                            category='设备维护',
                            amount=round(equipment_expense, 2),
                            note=random.choice(expense_categories['设备维护']),
                            created_by=random.choice(creators)
                        ))
                    
                    # 店铺租金：约占收入的8%
                    rent_expense = month_income * random.uniform(0.07, 0.09)
                    expense_date = month_start + timedelta(days=random.randint(0, 5))  # 月初交租金
                    expenses.append(Expense(
                        expense_date=expense_date,
                        category='店铺租金',
                        amount=round(rent_expense, 2),
                        note='店铺月租',
                        created_by='admin'
                    ))
                    
                    # 其他支出：约占收入的4%
                    other_expense_count = random.randint(1, 4)  # 每月1-4次其他支出
                    other_expense_total = month_income * random.uniform(0.03, 0.05)
                    for _ in range(other_expense_count):
                        amount = other_expense_total / other_expense_count * random.uniform(0.7, 1.3)
                        expense_date = month_start + timedelta(days=random.randint(0, (month_end - month_start).days))
                        expenses.append(Expense(
                            expense_date=expense_date,
                            category='其他支出',
                            amount=round(amount, 2),
                            note=random.choice(expense_categories['其他支出']),
                            created_by=random.choice(creators)
                        ))
            
            # 添加所有支出数据
            if expenses:
                db.session.add_all(expenses)
                db.session.commit()
                print(f'创建了{len(expenses)}条财务支出记录')
            else:
                print('没有找到订单数据，无法生成支出记录')
        
        # 检查是否已有分类数据
        if Category.query.first() is None:
            # 添加默认分类
            categories = [
                Category(id='french', name='法式面包'),
                Category(id='whole-wheat', name='全麦面包'),
                Category(id='specialty', name='特色面包'),
                Category(id='sweet', name='甜面包')
            ]
            db.session.add_all(categories)
            db.session.commit()

            # 添加示例面包数据
            breads = [
                Bread(
                    name='法式长棍',
                    price=15.00,
                    image='https://example.com/baguette.jpg',
                    category_id='french',
                    description='传统法式长棍面包，外酥里嫩',
                    ingredients={'面粉': '500g', '酵母': '10g', '盐': '10g', '水': '300ml'},
                    stock=20,
                    in_stock=True
                ),
                Bread(
                    name='全麦吐司',
                    price=18.00,
                    image='https://example.com/wholewheat.jpg',
                    category_id='whole-wheat',
                    description='健康全麦吐司，富含膳食纤维',
                    ingredients={'全麦粉': '400g', '高筋粉': '100g', '酵母': '8g', '糖': '20g', '盐': '8g'},
                    stock=15,
                    in_stock=True
                ),
                Bread(
                    name='巧克力可颂',
                    price=12.00,
                    image='https://example.com/croissant.jpg',
                    category_id='sweet',
                    description='酥脆可颂，内含巧克力馅',
                    ingredients={'面粉': '300g', '黄油': '150g', '巧克力': '100g', '糖': '30g', '酵母': '5g'},
                    stock=25,
                    in_stock=True
                ),
                Bread(
                    name='葡萄干面包',
                    price=16.00,
                    image='https://example.com/raisin.jpg',
                    category_id='specialty',
                    description='松软面包，搭配香甜葡萄干',
                    ingredients={'面粉': '400g', '葡萄干': '100g', '糖': '40g', '酵母': '8g', '盐': '6g'},
                    stock=18,
                    in_stock=True
                )
            ]
            db.session.add_all(breads)
            db.session.commit()

            # 添加示例订单数据（扩充模拟数据，便于财务分析）
            import random
            from datetime import timedelta
            names = ['张三', '李四', '王五', '赵六', '孙七', '周八', '吴九', '郑十']
            payment_methods = ['cash', 'wechat', 'alipay', 'card']
            status_list = ['completed', 'pending', 'processing', 'completed', 'cancelled']
            base_date = datetime(2024, 1, 1)
            orders = []
            order_items = []
            
            # 生成90天的订单数据，每天2-5个订单
            for day in range(1, 91):
                order_date = base_date + timedelta(days=day)
                # 周末订单量增加
                is_weekend = order_date.weekday() >= 5
                daily_orders = random.randint(4, 8) if is_weekend else random.randint(2, 5)
                
                for i in range(daily_orders):
                    customer_name = random.choice(names)
                    phone = f'138{random.randint(10000000, 99999999)}'
                    
                    # 生成订单编号
                    order_number = f"TB{order_date.strftime('%Y%m%d')}{str(i+1).zfill(3)}"
                    
                    # 随机生成订单状态，已完成订单占比较高
                    status = random.choices(
                        status_list, 
                        weights=[0.7, 0.1, 0.1, 0.05, 0.05],
                        k=1
                    )[0]
                    
                    # 随机生成支付方式，微信支付和支付宝占比较高
                    payment_method = random.choices(
                        payment_methods,
                        weights=[0.2, 0.4, 0.3, 0.1],
                        k=1
                    )[0]
                    
                    # 随机生成配送地址
                    has_address = random.random() > 0.7  # 30%的订单有配送地址
                    address = f"城市区域{random.randint(1, 5)}街道{random.randint(1, 20)}号" if has_address else None
                    
                    # 随机生成折扣和配送费
                    discount = round(random.choice([0, 5, 10, 15, 20]), 2) if random.random() > 0.7 else 0
                    delivery_fee = round(random.choice([0, 5, 8, 10]), 2) if has_address else 0
                    
                    # 创建订单
                    order = Order(
                        order_number=order_number,
                        customer_name=customer_name,
                        phone=phone,
                        address=address,
                        order_date=order_date + timedelta(hours=random.randint(8, 20), minutes=random.randint(0, 59)),
                        pickup_time=None if has_address else order_date + timedelta(hours=random.randint(1, 3)),
                        payment_method=payment_method,
                        status=status,
                        discount=discount,
                        delivery_fee=delivery_fee,
                        total_amount=0,  # 先设为0，后面计算
                        notes=random.choice(["请尽快送达", "不要辣", "多加糖", "少放盐", ""]) if random.random() > 0.8 else None
                    )
                    
                    orders.append(order)
            
            # 提交订单，获取ID
            db.session.add_all(orders)
            db.session.commit()
            
            # 为每个订单添加1-5个订单项
            for order in orders:
                # 随机选择1-5个面包
                num_items = random.randint(1, 5)
                total_amount = 0
                
                for _ in range(num_items):
                    bread = random.choice(breads)
                    quantity = random.randint(1, 3)
                    item_price = bread.price
                    
                    # 随机特价
                    if random.random() > 0.9:  # 10%概率特价
                        item_price = round(item_price * random.uniform(0.8, 0.95), 2)
                    
                    item_total = item_price * quantity
                    total_amount += item_total
                    
                    item = OrderItem(
                        order_id=order.id,
                        name=bread.name,
                        bread_type=bread.category_id,
                        price=item_price,
                        quantity=quantity
                    )
                    order_items.append(item)
                
                # 计算订单总金额（减去折扣，加上配送费）
                order.total_amount = round(total_amount - order.discount + order.delivery_fee, 2)
            
            # 提交订单项
            db.session.add_all(order_items)
            db.session.commit()
            
        # 添加默认用户
        if User.query.filter_by(username='admin').first() is None:
            admin_user = User(
                username='admin',
                password=generate_password_hash('admin123'),
                email='admin@example.com',
                phone='13888888888',
                role='admin',
                status='active'
            )
            staff_user = User(
                username='staff',
                password=generate_password_hash('staff123'),
                email='staff@example.com',
                phone='13777777777',
                role='staff',
                status='active'
            )
            db.session.add_all([admin_user, staff_user])
            db.session.commit()
            print('创建了默认用户：admin/admin123 和 staff/staff123')

# 面包分类路由
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([{
        'id': category.id,
        'name': category.name
    } for category in categories])

@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.json
    category = Category(id=data['id'], name=data['name'])
    db.session.add(category)
    db.session.commit()
    return jsonify({'message': '分类创建成功'}), 201

# 面包路由
@app.route('/api/breads', methods=['GET'])
def get_breads():
    category_id = request.args.get('category')
    search = request.args.get('search', '')
    
    query = Bread.query
    if category_id and category_id != 'all':
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Bread.name.ilike(f'%{search}%'))
    
    breads = query.all()
    return jsonify([{
        'id': bread.id,
        'name': bread.name,
        'price': bread.price,
        'image': bread.image,
        'categoryId': bread.category_id,
        'description': bread.description,
        'ingredients': bread.ingredients,
        'stock': bread.stock,
        'inStock': bread.in_stock
    } for bread in breads])

@app.route('/api/breads', methods=['POST'])
def create_bread():
    data = request.json
    bread = Bread(
        name=data['name'],
        price=data['price'],
        image=data.get('image', 'https://via.placeholder.com/80'),
        category_id=data['categoryId'],
        description=data['description'],
        ingredients=data['ingredients'],
        stock=data.get('stock', 0),
        in_stock=data.get('inStock', True)
    )
    db.session.add(bread)
    db.session.commit()
    return jsonify({'message': '面包创建成功', 'id': bread.id}), 201

@app.route('/api/breads/<int:bread_id>', methods=['PUT'])
def update_bread(bread_id):
    bread = Bread.query.get_or_404(bread_id)
    data = request.json
    
    # 只更新提供的字段
    if 'name' in data:
        bread.name = data['name']
    if 'price' in data:
        bread.price = data['price']
    if 'image' in data:
        bread.image = data['image']
    if 'categoryId' in data:
        bread.category_id = data['categoryId']
    if 'description' in data:
        bread.description = data['description']
    if 'ingredients' in data:
        bread.ingredients = data['ingredients']
    if 'stock' in data:
        bread.stock = data['stock']
    if 'inStock' in data:
        bread.in_stock = data['inStock']
    
    try:
        db.session.commit()
        return jsonify({'message': '面包信息更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': '更新失败', 'error': str(e)}), 400

# 添加专门的库存更新端点
@app.route('/api/breads/<int:bread_id>/stock', methods=['PUT'])
def update_bread_stock(bread_id):
    bread = Bread.query.get_or_404(bread_id)
    data = request.json
    
    if 'stock' in data:
        bread.stock = data['stock']
    if 'inStock' in data:
        bread.in_stock = data['inStock']
    
    try:
        db.session.commit()
        return jsonify({'message': '库存更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': '库存更新失败', 'error': str(e)}), 400

@app.route('/api/breads/<int:bread_id>', methods=['DELETE'])
def delete_bread(bread_id):
    bread = Bread.query.get_or_404(bread_id)
    db.session.delete(bread)
    db.session.commit()
    return jsonify({'message': '面包删除成功'})

# 订单路由
@app.route('/api/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    return jsonify([{
        'id': order.id,
        'orderNumber': order.order_number,
        'customerName': order.customer_name,
        'phone': order.phone,
        'address': order.address,
        'orderDate': order.order_date.isoformat(),
        'pickupTime': order.pickup_time.isoformat() if order.pickup_time else None,
        'paymentMethod': order.payment_method,
        'status': order.status,
        'discount': order.discount,
        'deliveryFee': order.delivery_fee,
        'totalAmount': order.total_amount,
        'notes': order.notes,
        'items': [{
            'id': item.id,
            'name': item.name,
            'breadType': item.bread_type,
            'price': item.price,
            'quantity': item.quantity
        } for item in order.items]
    } for order in orders])

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    
    # 生成订单编号，确保唯一性
    now = datetime.now()
    today_str = now.strftime('%Y%m%d')
    prefix = f"TB{today_str}"
    # 查询今天所有订单编号，找最大后缀
    today_orders = Order.query.filter(Order.order_number.like(f'{prefix}%')).all()
    max_suffix = 0
    for order in today_orders:
        try:
            suffix = int(order.order_number[-3:])
            if suffix > max_suffix:
                max_suffix = suffix
        except Exception:
            continue
    order_number = f"{prefix}{str(max_suffix + 1).zfill(3)}"
    
    # 创建订单
    order = Order(
        order_number=order_number,
        customer_name=data['customerName'],
        phone=data['phone'],
        address=data.get('address'),
        pickup_time=datetime.fromisoformat(data['pickupTime']) if data.get('pickupTime') else None,
        payment_method=data['paymentMethod'],
        status=data.get('status', 'pending'),
        discount=data.get('discount', 0.0),
        delivery_fee=data.get('deliveryFee', 0.0),
        total_amount=data['totalAmount'],
        notes=data.get('notes')
    )
    db.session.add(order)
    
    # 添加订单项
    for item_data in data['items']:
        item = OrderItem(
            name=item_data['name'],
            bread_type=item_data['breadType'],
            price=item_data['price'],
            quantity=item_data['quantity']
        )
        order.items.append(item)
    
    db.session.commit()
    return jsonify({
        'message': '订单创建成功',
        'id': order.id,
        'orderNumber': order.order_number
    }), 201

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.json
    
    # 更新订单基本信息
    order.customer_name = data.get('customerName', order.customer_name)
    order.phone = data.get('phone', order.phone)
    order.address = data.get('address', order.address)
    order.pickup_time = datetime.fromisoformat(data['pickupTime']) if data.get('pickupTime') else order.pickup_time
    order.payment_method = data.get('paymentMethod', order.payment_method)
    order.status = data.get('status', order.status)
    order.discount = data.get('discount', order.discount)
    order.delivery_fee = data.get('deliveryFee', order.delivery_fee)
    order.total_amount = data.get('totalAmount', order.total_amount)
    order.notes = data.get('notes', order.notes)
    
    # 更新订单项
    if 'items' in data:
        # 删除现有订单项
        for item in order.items:
            db.session.delete(item)
        
        # 添加新订单项
        for item_data in data['items']:
            item = OrderItem(
                name=item_data['name'],
                bread_type=item_data['breadType'],
                price=item_data['price'],
                quantity=item_data['quantity']
            )
            order.items.append(item)
    
    db.session.commit()
    return jsonify({'message': '订单更新成功'})

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({'message': '订单删除成功'})

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.json
    order.status = data['status']
    db.session.commit()
    return jsonify({'message': '订单状态更新成功'})

# 获取所有用户
@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'role': user.role,
        'status': user.status,
        'created_at': user.created_at.isoformat()
    } for user in users])

# 注册新用户
@app.route('/api/users/register', methods=['POST'])
def register_user():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': '用户名已存在'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': '邮箱已存在'}), 400
    
    user = User(
        username=data['username'],
        password=generate_password_hash(data['password']),
        email=data['email'],
        phone=data.get('phone', ''),
        role=data.get('role', 'staff'),
        status=data.get('status', 'active')
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': '注册成功', 'id': user.id}), 201

# 更新用户信息
@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': '用户名已存在'}), 400
        user.username = data['username']
    
    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': '邮箱已存在'}), 400
        user.email = data['email']
    
    if 'phone' in data:
        user.phone = data['phone']
    if 'role' in data:
        user.role = data['role']
    if 'status' in data:
        user.status = data['status']
    
    db.session.commit()
    return jsonify({'message': '用户信息更新成功'})

# 删除用户
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': '用户删除成功'})

# 用户登录
@app.route('/api/users/login', methods=['POST'])
def login_user():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        return jsonify({
            'message': '登录成功',
            'id': user.id,
            'username': user.username,
            'role': user.role
        })
    return jsonify({'message': '用户名或密码错误'}), 401

# 财务分析相关接口
@app.route('/api/finance/monthly-summary', methods=['GET'])
def get_monthly_summary():
    """获取当前月的财务概览数据"""
    # 获取查询参数，默认为当前月
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    # 计算当前月的起止时间
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # 计算上个月的起止时间，用于同比计算
    if month == 1:
        prev_month_start = datetime(year - 1, 12, 1)
        prev_month_end = datetime(year, 1, 1) - timedelta(days=1)
    else:
        prev_month_start = datetime(year, month - 1, 1)
        prev_month_end = start_date - timedelta(days=1)
    
    # 获取当前月的订单数据（收入）
    current_orders = Order.query.filter(
        Order.order_date >= start_date,
        Order.order_date <= end_date,
        Order.status == 'completed'
    ).all()
    
    # 获取上个月的订单数据（收入）
    prev_orders = Order.query.filter(
        Order.order_date >= prev_month_start,
        Order.order_date <= prev_month_end,
        Order.status == 'completed'
    ).all()
    
    # 获取当前月的支出数据
    current_expenses = Expense.query.filter(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date
    ).all()
    
    # 获取上个月的支出数据
    prev_expenses = Expense.query.filter(
        Expense.expense_date >= prev_month_start,
        Expense.expense_date <= prev_month_end
    ).all()
    
    # 计算当前月收入
    current_income = sum(order.total_amount for order in current_orders)
    
    # 计算上月收入
    prev_income = sum(order.total_amount for order in prev_orders)
    
    # 计算当前月支出
    current_expense = sum(expense.amount for expense in current_expenses)
    
    # 计算上月支出
    prev_expense = sum(expense.amount for expense in prev_expenses)
    
    # 计算利润
    current_profit = current_income - current_expense
    prev_profit = prev_income - prev_expense
    
    # 计算环比增长率
    income_trend = ((current_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    expense_trend = ((current_expense - prev_expense) / prev_expense * 100) if prev_expense > 0 else 0
    profit_trend = ((current_profit - prev_profit) / prev_profit * 100) if prev_profit > 0 else 0
    
    return jsonify({
        'monthlyIncome': round(current_income, 2),
        'monthlyExpense': round(current_expense, 2),
        'monthlyProfit': round(current_profit, 2),
        'incomeTrend': round(income_trend, 1),
        'expenseTrend': round(expense_trend, 1),
        'profitTrend': round(profit_trend, 1)
    })

@app.route('/api/finance/trends', methods=['GET'])
def get_finance_trends():
    """获取近6个月的财务趋势数据"""
    # 获取当前日期
    today = datetime.now()
    
    # 计算近6个月的数据
    months_data = []
    labels = []
    income_data = []
    expense_data = []
    profit_data = []
    
    for i in range(5, -1, -1):
        # 计算月份
        target_month = today.month - i
        target_year = today.year
        
        # 处理月份跨年的情况
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        # 计算该月的起止时间
        start_date = datetime(target_year, target_month, 1)
        if target_month == 12:
            end_date = datetime(target_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(target_year, target_month + 1, 1) - timedelta(days=1)
        
        # 获取该月的订单数据（收入）
        orders = Order.query.filter(
            Order.order_date >= start_date,
            Order.order_date <= end_date,
            Order.status == 'completed'
        ).all()
        
        # 获取该月的支出数据
        expenses = Expense.query.filter(
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date
        ).all()
        
        # 计算收入
        income = sum(order.total_amount for order in orders)
        
        # 计算支出
        expense = sum(expense.amount for expense in expenses)
        
        # 计算利润
        profit = income - expense
        
        # 添加月份标签
        month_label = f"{target_month}月"
        labels.append(month_label)
        
        # 添加数据
        income_data.append(round(income, 2))
        expense_data.append(round(expense, 2))
        profit_data.append(round(profit, 2))
    
    return jsonify({
        'labels': labels,
        'income': income_data,
        'expense': expense_data,
        'profit': profit_data
    })

@app.route('/api/finance/income-composition', methods=['GET'])
def get_income_composition():
    """获取收入构成数据"""
    # 获取查询参数
    start_date_str = request.args.get('startDate', '')
    end_date_str = request.args.get('endDate', '')
    
    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.split('T')[0])
        else:
            # 默认为当年1月1日
            start_date = datetime(datetime.now().year, 1, 1)
        
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.split('T')[0])
        else:
            # 默认为当前日期
            end_date = datetime.now()
    except ValueError:
        return jsonify({'error': '日期格式无效'}), 400
    
    # 获取指定日期范围的已完成订单
    orders = Order.query.filter(
        Order.order_date >= start_date,
        Order.order_date <= end_date,
        Order.status == 'completed'
    ).all()
    
    # 统计不同面包类型的销售额
    bread_sales = {}
    total_income = 0
    
    for order in orders:
        total_income += order.total_amount
        for item in order.items:
            category = get_bread_type_name(item.bread_type)
            if category not in bread_sales:
                bread_sales[category] = 0
            bread_sales[category] += item.price * item.quantity
    
    # 转换为饼图所需格式，并计算百分比
    result = []
    for category, amount in bread_sales.items():
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        result.append({
            'name': category,
            'value': round(amount, 2),
            'percentage': round(percentage, 1)
        })
    
    # 按金额降序排序
    result.sort(key=lambda x: x['value'], reverse=True)
    
    # 如果没有收入数据，添加一条空数据避免图表报错
    if not result:
        result = [{'name': '暂无收入', 'value': 0, 'percentage': 0}]
    
    return jsonify(result)

@app.route('/api/finance/expense-composition', methods=['GET'])
def get_expense_composition():
    """获取支出构成数据"""
    # 获取查询参数
    start_date_str = request.args.get('startDate', '')
    end_date_str = request.args.get('endDate', '')
    
    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.split('T')[0])
        else:
            # 默认为当年1月1日
            start_date = datetime(datetime.now().year, 1, 1)
        
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.split('T')[0])
        else:
            # 默认为当前日期
            end_date = datetime.now()
    except ValueError:
        return jsonify({'error': '日期格式无效'}), 400
    
    # 获取指定日期范围的支出数据
    expenses = Expense.query.filter(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date
    ).all()
    
    # 按类别统计支出
    expense_by_category = {}
    total_expense = 0
    
    for expense in expenses:
        category = expense.category
        if category not in expense_by_category:
            expense_by_category[category] = 0
        expense_by_category[category] += expense.amount
        total_expense += expense.amount
    
    # 转换为饼图所需格式，并计算百分比
    result = []
    for category, amount in expense_by_category.items():
        percentage = (amount / total_expense * 100) if total_expense > 0 else 0
        result.append({
            'name': category,
            'value': round(amount, 2),
            'percentage': round(percentage, 1)
        })
    
    # 按金额降序排序
    result.sort(key=lambda x: x['value'], reverse=True)
    
    # 如果没有支出数据，添加一条空数据避免图表报错
    if not result:
        result = [{'name': '暂无支出', 'value': 0, 'percentage': 0}]
    
    return jsonify(result)

@app.route('/api/finance/transactions', methods=['GET'])
def get_transactions():
    """获取财务交易明细"""
    # 获取查询参数
    start_date_str = request.args.get('startDate', '')
    end_date_str = request.args.get('endDate', '')
    
    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        else:
            # 默认为当年1月1日
            start_date = datetime(datetime.now().year, 1, 1)
        
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        else:
            # 默认为当前日期
            end_date = datetime.now()
    except ValueError:
        return jsonify({'error': '日期格式无效'}), 400
    
    # 获取订单数据（收入）
    orders = Order.query.filter(
        Order.order_date >= start_date,
        Order.order_date <= end_date,
        Order.status == 'completed'
    ).all()
    
    # 获取支出数据
    expenses = Expense.query.filter(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date
    ).all()
    
    transactions = []
    
    # 添加订单收入记录
    for order in orders:
        transactions.append({
            'id': f"income-{order.id}",
            'date': order.order_date.isoformat(),
            'type': 'income',
            'category': '面包销售',
            'amount': order.total_amount,
            'note': f"订单 #{order.order_number}"
        })
    
    # 添加支出记录
    for expense in expenses:
        transactions.append({
            'id': f"expense-{expense.id}",
            'date': expense.expense_date.isoformat(),
            'type': 'expense',
            'category': expense.category,
            'amount': expense.amount,
            'note': expense.note or '无备注'
        })
    
    # 按日期排序
    transactions.sort(key=lambda x: x['date'], reverse=True)
    
    return jsonify(transactions)

# 辅助函数，获取面包类型的中文名称
def get_bread_type_name(bread_type):
    bread_type_names = {
        'french': '法式面包',
        'whole-wheat': '全麦面包',
        'specialty': '特色面包',
        'sweet': '甜面包',
        'sourdough': '酸面团面包',
        'baguette': '法棍面包',
        'croissant': '牛角面包',
        'wholewheat': '全麦面包',
        'brioche': '布里欧面包',
        'rye': '黑麦面包',
        'ciabatta': '夏巴塔面包',
        'bagel': '贝果面包',
        'focaccia': '佛卡夏面包',
        'cake': '蛋糕',
        'other': '其他'
    }
    return bread_type_names.get(bread_type, bread_type)

# 支出管理相关接口
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """获取所有支出记录"""
    # 获取查询参数
    start_date_str = request.args.get('startDate', '')
    end_date_str = request.args.get('endDate', '')
    category = request.args.get('category', '')
    
    print(f"收到expenses请求，参数：startDate={start_date_str}, endDate={end_date_str}, category={category}")
    
    query = Expense.query
    
    # 按日期筛选
    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
            query = query.filter(Expense.expense_date >= start_date)
            print(f"开始日期: {start_date}")
        
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
            query = query.filter(Expense.expense_date <= end_date)
            print(f"结束日期: {end_date}")
    except ValueError as e:
        print(f"日期格式错误: {e}")
        return jsonify({'error': '日期格式无效'}), 400
    
    # 按类别筛选
    if category:
        query = query.filter(Expense.category == category)
        print(f"筛选类别: {category}")
    
    # 按日期倒序排序
    expenses = query.order_by(Expense.expense_date.desc()).all()
    print(f"查询到 {len(expenses)} 条支出记录")
    
    # 打印第一条记录（如果有的话）
    if expenses:
        print(f"第一条记录: {expenses[0].id}, {expenses[0].expense_date}, {expenses[0].amount}")
    
    result = [{
        'id': expense.id,
        'expenseDate': expense.expense_date.isoformat(),
        'category': expense.category,
        'amount': expense.amount,
        'note': expense.note,
        'createdBy': expense.created_by,
        'createdAt': expense.created_at.isoformat()
    } for expense in expenses]
    
    print(f"返回 {len(result)} 条记录")
    return jsonify(result)

@app.route('/api/expenses', methods=['POST'])
def create_expense():
    """创建新的支出记录"""
    data = request.json
    
    try:
        expense_date = datetime.fromisoformat(data['expenseDate'])
    except (ValueError, KeyError):
        return jsonify({'error': '日期格式无效'}), 400
    
    expense = Expense(
        expense_date=expense_date,
        category=data['category'],
        amount=data['amount'],
        note=data.get('note', ''),
        created_by=data.get('createdBy', 'admin')
    )
    
    db.session.add(expense)
    db.session.commit()
    
    return jsonify({
        'message': '支出记录创建成功',
        'id': expense.id
    }), 201

@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    """更新支出记录"""
    expense = Expense.query.get_or_404(expense_id)
    data = request.json
    
    if 'expenseDate' in data:
        try:
            expense.expense_date = datetime.fromisoformat(data['expenseDate'])
        except ValueError:
            return jsonify({'error': '日期格式无效'}), 400
    
    if 'category' in data:
        expense.category = data['category']
    
    if 'amount' in data:
        expense.amount = data['amount']
    
    if 'note' in data:
        expense.note = data['note']
    
    db.session.commit()
    
    return jsonify({'message': '支出记录更新成功'})

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    """删除支出记录"""
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    
    return jsonify({'message': '支出记录删除成功'})

@app.route('/api/expenses/categories', methods=['GET'])
def get_expense_categories():
    """获取所有支出类别"""
    # 从数据库中获取所有不同的支出类别
    categories = db.session.query(Expense.category).distinct().all()
    
    # 提取类别名称
    category_names = [category[0] for category in categories]
    
    # 如果数据库中没有类别，返回默认类别
    if not category_names:
        category_names = ['原料采购', '人工成本', '水电费用', '设备维护', '店铺租金', '其他支出']
    
    return jsonify(category_names)

if __name__ == '__main__':
    init_db()  # 初始化数据库
    app.run(debug=True, port=5050)
