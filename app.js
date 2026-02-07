const dataUrl = 'data.json';

const order = {
  deployments: ['公有云', '私有部署', '高可用部署'],
  licenses: ['按年订阅版', '三年订阅版', '一次性授权版'],
  products: [
    'ONES Project 项目管理平台',
    'ONES Wiki 知识库管理平台',
    'ONES Desk',
    'ONES Copilot'
  ]
};

const productMeta = {
  'ONES Project 项目管理平台': '基座产品，可单独售卖',
  'ONES Wiki 知识库管理平台': '基座产品，可单独售卖',
  'ONES Copilot': '跟随产品，需搭配基座产品',
  'ONES Desk': '跟随应用，需搭配 ONES Project'
};

const state = {
  data: null,
  selected: {},
  deployment: '',
  license: '',
  edition: '',
  discount: 100,
  serviceDays: 0,
  serviceRate: 3000,
  serviceDiscount: 100,
  availability: null,
  allDeployments: [],
  allLicenses: [],
  allEditions: [],
  combos: []
};

const deploymentSelect = document.getElementById('deployment');
const licenseSelect = document.getElementById('license');
const editionSelect = document.getElementById('edition');
const discountInput = document.getElementById('discount');
const serviceDaysInput = document.getElementById('serviceDays');
const serviceRateInput = document.getElementById('serviceRate');
const serviceDiscountInput = document.getElementById('serviceDiscount');
const productList = document.getElementById('productList');
const resultsTable = document.getElementById('resultsTable').querySelector('tbody');
const summaryEl = document.getElementById('summary');

const formatNumber = (value) => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'string') return value;
  return new Intl.NumberFormat('zh-CN').format(value);
};

const normalizeText = (v) => String(v || '').trim();

const isSubscription = (license) => license.includes('订阅');

const rangeIncludes = (range, seats) => {
  if (!range) return false;
  if (range.min !== undefined && range.max === null) {
    return seats >= range.min;
  }
  if (range.min !== undefined && range.max !== undefined) {
    return seats >= range.min && seats <= range.max;
  }
  return false;
};

const findRecord = (records, deployment, license, seats) => {
  return records.find((rec) => {
    return rec.deployment === deployment &&
      rec.license === license &&
      rangeIncludes(rec.seat_range, seats);
  });
};

const getOptions = (items, preferred) => {
  const uniq = Array.from(new Set(items.filter(Boolean)));
  if (preferred) {
    const inPreferred = preferred.filter((p) => uniq.includes(p));
    const rest = uniq.filter((u) => !preferred.includes(u));
    return [...inPreferred, ...rest];
  }
  return uniq;
};

const buildSelect = (selectEl, options) => {
  selectEl.innerHTML = '';
  options.forEach((opt) => {
    const option = document.createElement('option');
    option.value = opt;
    option.textContent = opt;
    selectEl.appendChild(option);
  });
};

const buildAvailability = () => {
  const availability = {};
  const combos = [];
  Object.values(state.data.products).forEach((product) => {
    product.records.forEach((record) => {
      const dep = record.deployment;
      const lic = record.license;
      if (!availability[dep]) availability[dep] = {};
      if (!availability[dep][lic]) availability[dep][lic] = {};
      Object.entries(record.editions).forEach(([ed, priceInfo]) => {
        if (priceInfo.list_price !== null && priceInfo.list_price !== undefined) {
          availability[dep][lic][ed] = true;
          combos.push({ dep, lic, ed });
        }
      });
    });
  });
  state.availability = availability;
  state.combos = combos;
};

const isComboAvailable = (dep, lic, ed) => {
  return !!(state.availability &&
    state.availability[dep] &&
    state.availability[dep][lic] &&
    state.availability[dep][lic][ed]);
};

const hasCombo = (dep, lic, ed) => {
  return state.combos.some((c) => {
    if (dep && c.dep !== dep) return false;
    if (lic && c.lic !== lic) return false;
    if (ed && c.ed !== ed) return false;
    return true;
  });
};

const getLicenseOptions = (deployment, edition) => {
  let result = state.allLicenses.filter((lic) =>
    hasCombo(deployment, lic, edition)
  );
  if (result.length) return result;
  result = state.allLicenses.filter((lic) => hasCombo(deployment, lic, null));
  if (result.length) return result;
  return state.allLicenses;
};

const getEditionOptions = (deployment, license) => {
  let result = state.allEditions.filter((ed) =>
    hasCombo(deployment, license, ed)
  );
  if (result.length) return result;
  result = state.allEditions.filter((ed) => hasCombo(deployment, null, ed));
  if (result.length) return result;
  return state.allEditions;
};

const syncSelect = (selectEl, options, currentValue) => {
  buildSelect(selectEl, options);
  if (options.includes(currentValue)) {
    selectEl.value = currentValue;
    return currentValue;
  }
  const next = options[0] || '';
  selectEl.value = next;
  return next;
};

const updateSelects = (changed) => {
  const deploymentOptions = state.allDeployments;
  const licenseOptions = getLicenseOptions(state.deployment, state.edition);
  const editionOptions = getEditionOptions(state.deployment, state.license);

  state.deployment = syncSelect(deploymentSelect, deploymentOptions, state.deployment);
  state.license = syncSelect(licenseSelect, licenseOptions, state.license);
  state.edition = syncSelect(editionSelect, editionOptions, state.edition);
};

const buildProducts = () => {
  productList.innerHTML = '';
  order.products.forEach((product) => {
    if (!state.data.products[product]) return;

    const card = document.createElement('div');
    card.className = 'product-card';

    const head = document.createElement('div');
    head.className = 'product-head';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `product-${product}`;
    checkbox.checked = product === 'ONES Project 项目管理平台';

    const title = document.createElement('div');
    title.className = 'product-title';
    title.textContent = product;

    head.appendChild(checkbox);
    head.appendChild(title);

    const meta = document.createElement('div');
    meta.className = 'product-meta';
    meta.textContent = productMeta[product] || '';

    const seatField = document.createElement('div');
    seatField.className = 'field';
    const seatLabel = document.createElement('label');
    seatLabel.textContent = '账号数量';
    const seatInput = document.createElement('input');
    seatInput.type = 'number';
    seatInput.min = '1';
    seatInput.value = '10';
    seatInput.disabled = !checkbox.checked;

    seatField.appendChild(seatLabel);
    seatField.appendChild(seatInput);

    checkbox.addEventListener('change', () => {
      seatInput.disabled = !checkbox.checked;
      state.selected[product].enabled = checkbox.checked;
      compute();
    });

    seatInput.addEventListener('input', () => {
      const value = parseInt(seatInput.value || '0', 10);
      state.selected[product].seats = isNaN(value) ? 0 : value;
      compute();
    });

    card.appendChild(head);
    card.appendChild(meta);
    card.appendChild(seatField);
    productList.appendChild(card);

    state.selected[product] = {
      enabled: checkbox.checked,
      seats: parseInt(seatInput.value, 10)
    };
  });
};

const compute = () => {
  resultsTable.innerHTML = '';
  summaryEl.classList.remove('warning');
  const selectedProducts = Object.entries(state.selected)
    .filter(([, info]) => info.enabled);

  const hasService = (state.serviceDays || 0) > 0;
  if (selectedProducts.length === 0 && !hasService) {
    summaryEl.textContent = '请先选择至少一个产品模块';
    return;
  }

  let total = 0;
  let hasContact = false;
  let hasMissing = false;

  selectedProducts.forEach(([product, info]) => {
    const seats = info.seats || 0;
    const records = state.data.products[product].records;
    const record = findRecord(records, state.deployment, state.license, seats);

    let listPrice = null;
    let unitPrice = null;
    let status = '可计算';
    let rangeText = '-';

    if (!record) {
      if (seats >= 10000) {
        status = '请联系我们';
        hasContact = true;
      } else {
        status = '未找到匹配区间';
        hasMissing = true;
      }
    } else {
      const edition = record.editions[state.edition];
      rangeText = record.seat_range && record.seat_range.max
        ? `${record.seat_range.min} - ${record.seat_range.max}`
        : record.seat_range && record.seat_range.max === null
          ? `${record.seat_range.min}+`
          : '-';

      if (!edition || edition.list_price === null) {
        // 特殊：公有云 Copilot 随基座赠送
        if (product === 'ONES Copilot' && state.deployment === '公有云') {
          listPrice = 0;
          unitPrice = 0;
          status = '公有云随基座赠送（含用量限制）';
        } else {
          status = '请联系我们';
          hasContact = true;
        }
      } else {
        listPrice = edition.list_price;
        unitPrice = edition.unit_price;
        total += listPrice;
      }
    }

    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${product}</td>
      <td>${formatNumber(seats)}</td>
      <td>${rangeText}</td>
      <td>${listPrice === null ? '-' : formatNumber(listPrice)}</td>
      <td>${unitPrice === null ? '-' : formatNumber(unitPrice)}</td>
      <td>${status}</td>
    `;
    resultsTable.appendChild(row);
  });

  const serviceDays = Math.max(0, Number(state.serviceDays) || 0);
  const serviceRate = Math.max(0, Number(state.serviceRate) || 0);
  const serviceDiscountRate = Math.max(0, Math.min(100, Number(state.serviceDiscount) || 0));
  const serviceSubtotal = serviceDays * serviceRate;
  const serviceTotal = serviceSubtotal * (serviceDiscountRate / 100);

  if (serviceDays > 0) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>服务人天</td>
      <td>${formatNumber(serviceDays)}</td>
      <td>-</td>
      <td>${formatNumber(serviceSubtotal)}</td>
      <td>-</td>
      <td>折扣 ${serviceDiscountRate}%</td>
    `;
    resultsTable.appendChild(row);
  }

  if (hasContact) {
    summaryEl.textContent = '部分选项需要人工报价，请联系商务确认。';
    return;
  }

  if (hasMissing) {
    summaryEl.textContent = '存在未匹配区间，请检查账号数或选择项。';
    return;
  }

  const discountRate = Math.max(0, Math.min(100, Number(state.discount) || 0));
  const discountedTotal = total * (discountRate / 100);
  const combinedTotal = discountedTotal + serviceTotal;

  let adjusted = combinedTotal;
  let adjustmentNote = '';

  if (state.deployment === '私有部署') {
    const min = isSubscription(state.license)
      ? state.data.notes.private_min_subscription
      : state.data.notes.private_min_perpetual;
    if (discountedTotal > 0 && discountedTotal < min) {
      summaryEl.classList.add('warning');
      adjustmentNote = `，折扣后低于起售门槛（${formatNumber(min)} 元起售）`;
    }
  }

  summaryEl.textContent = `小计：${formatNumber(total)} 元，折扣：${discountRate}% ，服务费：${formatNumber(serviceTotal)} 元，总计：${formatNumber(adjusted)} 元${adjustmentNote}`;
};

const resetForm = () => {
  deploymentSelect.selectedIndex = 0;
  licenseSelect.selectedIndex = 0;
  editionSelect.selectedIndex = 0;
  discountInput.value = '100';
  state.deployment = deploymentSelect.value;
  state.license = licenseSelect.value;
  state.edition = editionSelect.value;
  state.discount = 100;
  serviceDaysInput.value = '0';
  serviceRateInput.value = '3000';
  serviceDiscountInput.value = '100';
  state.serviceDays = 0;
  state.serviceRate = 3000;
  state.serviceDiscount = 100;

  buildProducts();
  resultsTable.innerHTML = '';
  summaryEl.textContent = '请先选择产品与参数';
};

const init = async () => {
  if (window.__ONES_DATA__) {
    state.data = window.__ONES_DATA__;
  } else {
    const res = await fetch(dataUrl);
    state.data = await res.json();
  }

  const allRecords = Object.values(state.data.products)
    .flatMap((p) => p.records);

  const deployments = getOptions(
    allRecords.map((r) => r.deployment),
    order.deployments
  );
  const licenses = getOptions(
    allRecords.map((r) => r.license),
    order.licenses
  );
  const editions = state.data.products[order.products[0]].editions;

  state.allDeployments = deployments;
  state.allLicenses = licenses;
  state.allEditions = editions;
  buildAvailability();

  buildSelect(deploymentSelect, deployments);
  buildSelect(licenseSelect, licenses);
  buildSelect(editionSelect, editions);

  state.deployment = deploymentSelect.value;
  state.license = licenseSelect.value;
  state.edition = editionSelect.value;
  state.discount = Number(discountInput.value || 100);
  state.serviceDays = Number(serviceDaysInput.value || 0);
  state.serviceRate = Number(serviceRateInput.value || 0);
  state.serviceDiscount = Number(serviceDiscountInput.value || 100);

  buildProducts();
  updateSelects();

  deploymentSelect.addEventListener('change', () => {
    state.deployment = deploymentSelect.value;
    updateSelects('deployment');
    compute();
  });
  licenseSelect.addEventListener('change', () => {
    state.license = licenseSelect.value;
    updateSelects('license');
    compute();
  });
  editionSelect.addEventListener('change', () => {
    state.edition = editionSelect.value;
    updateSelects('edition');
    compute();
  });
  discountInput.addEventListener('input', () => {
    state.discount = Number(discountInput.value || 0);
    compute();
  });
  serviceDaysInput.addEventListener('input', () => {
    state.serviceDays = Number(serviceDaysInput.value || 0);
    compute();
  });
  serviceRateInput.addEventListener('input', () => {
    state.serviceRate = Number(serviceRateInput.value || 0);
    compute();
  });
  serviceDiscountInput.addEventListener('input', () => {
    state.serviceDiscount = Number(serviceDiscountInput.value || 0);
    compute();
  });

  document.getElementById('calcBtn').addEventListener('click', compute);
  document.getElementById('resetBtn').addEventListener('click', resetForm);
};

init();
