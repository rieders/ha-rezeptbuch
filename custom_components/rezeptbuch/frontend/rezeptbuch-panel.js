// node_modules/@mdi/js/mdi.js
var e = "M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z", t = "M4,4H7L9,2H15L17,4H20A2,2 0 0,1 22,6V18A2,2 0 0,1 20,20H4A2,2 0 0,1 2,18V6A2,2 0 0,1 4,4M12,7A5,5 0 0,0 7,12A5,5 0 0,0 12,17A5,5 0 0,0 17,12A5,5 0 0,0 12,7M12,9A3,3 0 0,1 15,12A3,3 0 0,1 12,15A3,3 0 0,1 9,12A3,3 0 0,1 12,9Z", n = "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z", r = "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z", i = "M8,12H16V14H8V12M10,20H6V4H13V9H18V12.1L20,10.1V8L14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H10V20M8,18H12.1L13,17.1V16H8V18M20.2,13C20.3,13 20.5,13.1 20.6,13.2L21.9,14.5C22.1,14.7 22.1,15.1 21.9,15.3L20.9,16.3L18.8,14.2L19.8,13.2C19.9,13.1 20,13 20.2,13M20.2,16.9L14.1,23H12V20.9L18.1,14.8L20.2,16.9Z", a = "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z", o = "M12,20A7,7 0 0,1 5,13A7,7 0 0,1 12,6A7,7 0 0,1 19,13A7,7 0 0,1 12,20M19.03,7.39L20.45,5.97C20,5.46 19.55,5 19.04,4.56L17.62,6C16.07,4.74 14.12,4 12,4A9,9 0 0,0 3,13A9,9 0 0,0 12,22C17,22 21,17.97 21,13C21,10.88 20.26,8.93 19.03,7.39M11,14H13V8H11M15,1H9V3H15V1Z", s = globalThis, c = s.ShadowRoot && (s.ShadyCSS === void 0 || s.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, l = Symbol(), u = /* @__PURE__ */ new WeakMap(), d = class {
	constructor(e, t, n) {
		if (this._$cssResult$ = !0, n !== l) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, t = this.t;
		if (c && e === void 0) {
			let n = t !== void 0 && t.length === 1;
			n && (e = u.get(t)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), n && u.set(t, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, ee = (e) => new d(typeof e == "string" ? e : e + "", void 0, l), f = (e, ...t) => new d(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, l), te = (e, t) => {
	if (c) e.adoptedStyleSheets = t.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let n of t) {
		let t = document.createElement("style"), r = s.litNonce;
		r !== void 0 && t.setAttribute("nonce", r), t.textContent = n.cssText, e.appendChild(t);
	}
}, ne = c ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return ee(t);
})(e) : e, { is: re, defineProperty: ie, getOwnPropertyDescriptor: ae, getOwnPropertyNames: oe, getOwnPropertySymbols: se, getPrototypeOf: ce } = Object, p = globalThis, le = p.trustedTypes, ue = le ? le.emptyScript : "", de = p.reactiveElementPolyfillSupport, m = (e, t) => e, h = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? ue : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, fe = (e, t) => !re(e, t), pe = {
	attribute: !0,
	type: String,
	converter: h,
	reflect: !1,
	useDefault: !1,
	hasChanged: fe
};
Symbol.metadata ??= Symbol("metadata"), p.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var g = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = pe) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && ie(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = ae(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? pe;
	}
	static _$Ei() {
		if (this.hasOwnProperty(m("elementProperties"))) return;
		let e = ce(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(m("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(m("properties"))) {
			let e = this.properties, t = [...oe(e), ...se(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(ne(e));
		} else e !== void 0 && t.push(ne(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return te(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? h : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? h : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? fe)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
g.elementStyles = [], g.shadowRootOptions = { mode: "open" }, g[m("elementProperties")] = /* @__PURE__ */ new Map(), g[m("finalized")] = /* @__PURE__ */ new Map(), de?.({ ReactiveElement: g }), (p.reactiveElementVersions ??= []).push("2.1.2");
// node_modules/lit-html/lit-html.js
var _ = globalThis, me = (e) => e, v = _.trustedTypes, he = v ? v.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, ge = "$lit$", y = `lit$${Math.random().toFixed(9).slice(2)}$`, _e = "?" + y, ve = `<${_e}>`, b = document, x = () => b.createComment(""), S = (e) => e === null || typeof e != "object" && typeof e != "function", C = Array.isArray, ye = (e) => C(e) || typeof e?.[Symbol.iterator] == "function", w = "[ 	\n\f\r]", T = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, be = /-->/g, xe = />/g, E = RegExp(`>|${w}(?:([^\\s"'>=/]+)(${w}*=${w}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), Se = /'/g, Ce = /"/g, we = /^(?:script|style|textarea|title)$/i, Te = (e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}), D = Te(1), Ee = Te(2), O = Symbol.for("lit-noChange"), k = Symbol.for("lit-nothing"), De = /* @__PURE__ */ new WeakMap(), A = b.createTreeWalker(b, 129);
function Oe(e, t) {
	if (!C(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return he === void 0 ? t : he.createHTML(t);
}
var ke = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = T;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === T ? c[1] === "!--" ? o = be : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = E) : (we.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = E) : o = xe : o === E ? c[0] === ">" ? (o = i ?? T, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? E : c[3] === "\"" ? Ce : Se) : o === Ce || o === Se ? o = E : o === be || o === xe ? o = T : (o = E, i = void 0);
		let d = o === E && e[t + 1].startsWith("/>") ? " " : "";
		a += o === T ? n + ve : l >= 0 ? (r.push(s), n.slice(0, l) + ge + n.slice(l) + y + d) : n + y + (l === -2 ? t : d);
	}
	return [Oe(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, j = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = ke(t, n);
		if (this.el = e.createElement(l, r), A.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = A.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(ge)) {
					let t = u[o++], n = i.getAttribute(e).split(y), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? je : r[1] === "?" ? Me : r[1] === "@" ? Ne : P
					}), i.removeAttribute(e);
				} else e.startsWith(y) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (we.test(i.tagName)) {
					let e = i.textContent.split(y), t = e.length - 1;
					if (t > 0) {
						i.textContent = v ? v.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], x()), A.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], x());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === _e) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(y, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += y.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = b.createElement("template");
		return n.innerHTML = e, n;
	}
};
function M(e, t, n = e, r) {
	if (t === O) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = S(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = M(e, i._$AS(e, t.values), i, r)), t;
}
var Ae = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? b).importNode(t, !0);
		A.currentNode = r;
		let i = A.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new N(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new Pe(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = A.nextNode(), a++);
		}
		return A.currentNode = b, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, N = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = k, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = M(this, e, t), S(e) ? e === k || e == null || e === "" ? (this._$AH !== k && this._$AR(), this._$AH = k) : e !== this._$AH && e !== O && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? ye(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== k && S(this._$AH) ? this._$AA.nextSibling.data = e : this.T(b.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = j.createElement(Oe(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new Ae(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = De.get(e.strings);
		return t === void 0 && De.set(e.strings, t = new j(e)), t;
	}
	k(t) {
		C(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(x()), this.O(x()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = me(e).nextSibling;
			me(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, P = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = k, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = k;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = M(this, e, t, 0), a = !S(e) || e !== this._$AH && e !== O, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = M(this, r[n + o], t, o), s === O && (s = this._$AH[o]), a ||= !S(s) || s !== this._$AH[o], s === k ? e = k : e !== k && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === k ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, je = class extends P {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === k ? void 0 : e;
	}
}, Me = class extends P {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== k);
	}
}, Ne = class extends P {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = M(this, e, t, 0) ?? k) === O) return;
		let n = this._$AH, r = e === k && n !== k || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== k && (n === k || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, Pe = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		M(this, e);
	}
}, Fe = _.litHtmlPolyfillSupport;
Fe?.(j, N), (_.litHtmlVersions ??= []).push("3.3.3");
var Ie = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new N(t.insertBefore(x(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, F = globalThis, I = class extends g {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Ie(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return O;
	}
};
I._$litElement$ = !0, I.finalized = !0, F.litElementHydrateSupport?.({ LitElement: I });
var Le = F.litElementPolyfillSupport;
Le?.({ LitElement: I }), (F.litElementVersions ??= []).push("4.2.2");
// src/api.ts
function Re(e) {
	if (e && typeof e == "object") {
		let t = e;
		return {
			code: String(t.code ?? "unknown_error"),
			message: String(t.message ?? "")
		};
	}
	return {
		code: "unknown_error",
		message: String(e)
	};
}
var ze = class {
	constructor(e) {
		this.getHass = e;
	}
	get hass() {
		return this.getHass();
	}
	ws(e, t = {}) {
		return this.hass.callWS({
			type: `rezeptbuch/${e}`,
			...t
		});
	}
	info() {
		return this.ws("info");
	}
	list(e) {
		let t = { ...e };
		for (let e of Object.keys(t)) (t[e] === void 0 || t[e] === "") && delete t[e];
		return this.ws("recipes/list", t);
	}
	recipe(e, t, n) {
		return this.ws("recipe/get", {
			recipe_id: e,
			...t ? { version_id: t } : {},
			...n ? { servings: n } : {}
		});
	}
	diff(e, t) {
		return this.ws("recipe/diff", {
			old_version_id: e,
			new_version_id: t
		});
	}
	setDefaultVersion(e, t) {
		return this.ws("recipe/set_default_version", {
			recipe_id: e,
			version_id: t
		});
	}
	rate(e, t, n, r, i) {
		return this.ws("recipe/rate", {
			recipe_id: e,
			stars: t,
			comment: n || null,
			cooked: r,
			...i ? { version_id: i } : {}
		});
	}
	annotate(e, t) {
		return this.ws("recipe/annotate", {
			recipe_id: e,
			text: t
		});
	}
	deleteRecipe(e) {
		return this.ws("recipe/delete", { recipe_id: e });
	}
	categories() {
		return this.ws("categories");
	}
	tags() {
		return this.ws("tags");
	}
	drafts() {
		return this.ws("drafts");
	}
	draft(e) {
		return this.ws("draft/get", { draft_id: e });
	}
	updateDraft(e, t) {
		return this.ws("draft/update", {
			draft_id: e,
			...t
		});
	}
	confirmDraft(e, t = !1) {
		return this.ws("draft/confirm", {
			draft_id: e,
			allow_duplicate: t
		});
	}
	discardDraft(e) {
		return this.ws("draft/discard", { draft_id: e });
	}
	importUrl(e, t = !1) {
		return this.ws("import/url", {
			url: e,
			allow_duplicate: t
		});
	}
	addToShoppingList(e, t) {
		return this.ws("shopping/add", {
			recipe_id: e,
			...t ? { servings: t } : {}
		});
	}
	async uploadPhotos(e) {
		let t = new FormData();
		e.forEach((e, n) => t.append("photo", e, `seite-${n + 1}.jpg`));
		let n = "/api/rezeptbuch/import/photo", r;
		if (this.hass.fetchWithAuth) r = await this.hass.fetchWithAuth(n, {
			method: "POST",
			body: t
		});
		else {
			let e = this.hass.auth?.accessToken ?? this.hass.auth?.data?.access_token ?? "";
			r = await fetch(n, {
				method: "POST",
				body: t,
				headers: { Authorization: `Bearer ${e}` }
			});
		}
		let i = await r.json().catch(() => ({}));
		if (!r.ok) throw {
			code: i.code ?? `http_${r.status}`,
			message: i.message ?? r.statusText
		};
		return i;
	}
}, L, Be = class extends I {
	render() {
		return D`<svg viewBox="0 0 24 24" aria-hidden="true">${Ee`<path d=${this.path ?? ""}></path>`}</svg>`;
	}
};
L = Be, L.properties = { path: { type: String } }, L.styles = f`
    :host {
      display: inline-flex;
      width: var(--rb-icon-size, 24px);
      height: var(--rb-icon-size, 24px);
      flex: none;
    }
    svg {
      width: 100%;
      height: 100%;
      fill: currentColor;
    }
  `, customElements.get("rb-icon") || customElements.define("rb-icon", Be);
// src/format.ts
function R(e, t) {
	if (!t || t <= 0) return "";
	let n = Math.floor(t / 60), r = Math.round(t % 60);
	return n ? r ? e("common.hours_minutes", {
		h: n,
		m: r
	}) : e("common.hours", { h: n }) : e("common.minutes", { n: r });
}
function Ve(e) {
	let t = Math.max(0, Math.ceil(e / 1e3)), n = Math.floor(t / 3600), r = Math.floor(t % 3600 / 60), i = t % 60, a = n ? String(r).padStart(2, "0") : String(r);
	return `${n ? `${n}:` : ""}${a}:${String(i).padStart(2, "0")}`;
}
function He(e, t, n = 1) {
	return new Intl.NumberFormat(e.startsWith("de") ? "de-DE" : "en-US", { maximumFractionDigits: n }).format(t);
}
function z(e, t) {
	if (!t) return "";
	let n = new Date(t);
	return Number.isNaN(n.getTime()) ? "" : new Intl.DateTimeFormat(e.startsWith("de") ? "de-DE" : "en-US", { dateStyle: "medium" }).format(n);
}
function Ue(e) {
	return e.split(/\n\s*\n/).map((e) => e.replace(/\s*\n\s*/g, " ").trim()).filter(Boolean);
}
function We(e) {
	return e.split("\n").map((e) => e.trim()).filter(Boolean);
}
function Ge(e) {
	return [...new Set(e.split(",").map((e) => e.trim()).filter(Boolean))];
}
// src/styles.ts
var B = f`
  :host {
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, system-ui, sans-serif));
    -webkit-tap-highlight-color: transparent;
  }
  * {
    box-sizing: border-box;
  }
  .card {
    background: var(--card-background-color, #fff);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0, 0, 0, 0.2));
    border: var(--ha-card-border-width, 0) solid var(--divider-color);
    padding: 16px;
  }
  h1,
  h2,
  h3 {
    margin: 0 0 8px;
    font-weight: 500;
  }
  h1 {
    font-size: 1.5rem;
  }
  h2 {
    font-size: 1.2rem;
  }
  h3 {
    font-size: 1rem;
  }
  button,
  .btn {
    font: inherit;
    min-height: 44px;
    min-width: 44px;
    padding: 0 14px;
    border-radius: 22px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color, transparent);
    color: var(--primary-text-color);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    text-decoration: none;
  }
  button.primary {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  button.danger {
    color: var(--error-color, #db4437);
    border-color: var(--error-color, #db4437);
  }
  button.icon {
    padding: 0;
    border: none;
    background: transparent;
    border-radius: 50%;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  button:focus-visible,
  input:focus-visible,
  select:focus-visible,
  textarea:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
  input,
  select,
  textarea {
    font: inherit;
    color: var(--primary-text-color);
    background: var(--secondary-background-color, var(--card-background-color));
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    min-height: 44px;
    padding: 8px 12px;
    width: 100%;
  }
  textarea {
    min-height: 160px;
    resize: vertical;
    line-height: 1.5;
  }
  label {
    display: block;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
    margin: 12px 0 4px;
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .grow {
    flex: 1 1 auto;
  }
  .warning {
    background: color-mix(in srgb, var(--warning-color, #ffa600) 18%, transparent);
    border-left: 4px solid var(--warning-color, #ffa600);
    padding: 8px 12px;
    border-radius: 6px;
  }
  .error {
    background: color-mix(in srgb, var(--error-color, #db4437) 15%, transparent);
    border-left: 4px solid var(--error-color, #db4437);
    padding: 8px 12px;
    border-radius: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 0 10px;
    border-radius: 14px;
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
    font-size: 0.85rem;
  }
  img {
    max-width: 100%;
  }
`, Ke = class extends EventTarget {
	constructor(e) {
		super(), this.env = e, this.timers = [], this.soundBlocked = !1, this.handle = null, this.audio = null, this.seq = 0;
	}
	start(e, t, n) {
		this.unlockAudio();
		let r = {
			id: `t${++this.seq}`,
			label: e,
			recipeId: t,
			durationMs: n * 1e3,
			endsAt: this.env.now() + n * 1e3,
			remainingMs: n * 1e3,
			state: "running"
		};
		return this.timers = [...this.timers, r], this.ensureTicking(), this.changed(), r;
	}
	pause(e) {
		this.update(e, (e) => e.state === "running" ? {
			...e,
			state: "paused",
			remainingMs: this.remaining(e),
			endsAt: null
		} : e), this.stopTickingIfIdle();
	}
	resume(e) {
		this.unlockAudio(), this.update(e, (e) => e.state === "paused" ? {
			...e,
			state: "running",
			endsAt: this.env.now() + e.remainingMs
		} : e), this.ensureTicking();
	}
	remove(e) {
		this.timers = this.timers.filter((t) => t.id !== e), this.stopTickingIfIdle(), this.changed();
	}
	remaining(e) {
		return e.state === "running" && e.endsAt !== null ? Math.max(0, e.endsAt - this.env.now()) : e.remainingMs;
	}
	tick() {
		let e = !1;
		this.timers = this.timers.map((t) => t.state === "running" && this.remaining(t) <= 0 ? (e = !0, {
			...t,
			state: "done",
			remainingMs: 0,
			endsAt: null
		}) : t), e && this.alarm(), this.stopTickingIfIdle(), this.changed();
	}
	alarm() {
		this.env.vibrate([
			400,
			200,
			400,
			200,
			400
		]), this.audio && this.audio.state === "running" ? (this.audio.beep(), this.soundBlocked = !1) : this.soundBlocked = !0;
	}
	unlockAudio() {
		try {
			if (this.audio ??= this.env.createAudio(), !this.audio) {
				this.soundBlocked = !0;
				return;
			}
			this.audio.state === "running" ? this.soundBlocked = !1 : this.audio.resume().then(() => {
				this.soundBlocked = this.audio?.state !== "running", this.changed();
			}).catch(() => {
				this.soundBlocked = !0, this.changed();
			});
		} catch {
			this.soundBlocked = !0;
		}
	}
	update(e, t) {
		this.timers = this.timers.map((n) => n.id === e ? t(n) : n), this.changed();
	}
	ensureTicking() {
		this.handle === null && this.timers.some((e) => e.state === "running") && (this.handle = this.env.setInterval(() => this.tick(), 500));
	}
	stopTickingIfIdle() {
		this.handle !== null && !this.timers.some((e) => e.state === "running") && (this.env.clearInterval(this.handle), this.handle = null);
	}
	changed() {
		this.dispatchEvent(new Event("change"));
	}
};
function qe() {
	let e = globalThis.AudioContext ?? globalThis.webkitAudioContext;
	if (!e) return null;
	let t = new e();
	return {
		get state() {
			return t.state;
		},
		resume: () => t.resume(),
		beep() {
			let e = t.currentTime;
			for (let n = 0; n < 3; n++) {
				let r = t.createOscillator(), i = t.createGain();
				r.type = "sine", r.frequency.value = 880, i.gain.setValueAtTime(1e-4, e + n * .6), i.gain.exponentialRampToValueAtTime(.4, e + n * .6 + .02), i.gain.exponentialRampToValueAtTime(1e-4, e + n * .6 + .4), r.connect(i).connect(t.destination), r.start(e + n * .6), r.stop(e + n * .6 + .45);
			}
		}
	};
}
var V = new Ke({
	now: () => Date.now(),
	setInterval: (e, t) => globalThis.setInterval(e, t),
	clearInterval: (e) => globalThis.clearInterval(e),
	createAudio: qe,
	vibrate: (e) => {
		try {
			globalThis.navigator?.vibrate?.(e);
		} catch {}
	}
}), H, Je = class extends I {
	constructor(...e) {
		super(...e), this.onChange = () => this.requestUpdate();
	}
	connectedCallback() {
		super.connectedCallback(), V.addEventListener("change", this.onChange), this.clock = setInterval(() => V.timers.length && this.requestUpdate(), 1e3);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), V.removeEventListener("change", this.onChange), clearInterval(this.clock);
	}
	render() {
		let e = this.t, t = V.timers;
		if (!t.length) return k;
		let r = t.some((e) => e.state === "done");
		return D`<div class="bar" role="timer" aria-live="polite">
      ${t.map((t) => D`<div class="timer ${t.state === "done" ? "done" : ""}">
          <rb-icon .path=${o}></rb-icon>
          <span class="time">${Ve(V.remaining(t))}</span>
          <span class="label">${t.state === "done" ? e("timer.done", { label: t.label }) : t.label}</span>
          ${t.state === "running" ? D`<button class="icon" aria-label=${e("timer.pause")} @click=${() => V.pause(t.id)}>
                <rb-icon .path=${"M14,19H18V5H14M6,19H10V5H6V19Z"}></rb-icon>
              </button>` : t.state === "paused" ? D`<button class="icon" aria-label=${e("timer.resume")} @click=${() => V.resume(t.id)}>
                  <rb-icon .path=${"M8,5.14V19.14L19,12.14L8,5.14Z"}></rb-icon>
                </button>` : k}
          <button
            class="icon"
            aria-label=${t.state === "done" ? e("timer.dismiss") : e("timer.stop")}
            @click=${() => V.remove(t.id)}
          >
            <rb-icon .path=${n}></rb-icon>
          </button>
        </div>`)}
      ${V.soundBlocked && (r || t.length) ? D`<div class="hint warning row"><rb-icon .path=${"M12,4L9.91,6.09L12,8.18M4.27,3L3,4.27L7.73,9H3V15H7L12,20V13.27L16.25,17.53C15.58,18.04 14.83,18.46 14,18.7V20.77C15.38,20.45 16.63,19.82 17.68,18.96L19.73,21L21,19.73L12,10.73M19,12C19,12.94 18.8,13.82 18.46,14.64L19.97,16.15C20.62,14.91 21,13.5 21,12C21,7.72 18,4.14 14,3.23V5.29C16.89,6.15 19,8.83 19,12M16.5,12C16.5,10.23 15.5,8.71 14,7.97V10.18L16.45,12.63C16.5,12.43 16.5,12.21 16.5,12Z"}></rb-icon>${e("timer.no_sound")}</div>` : k}
    </div>`;
	}
};
H = Je, H.properties = { t: { attribute: !1 } }, H.styles = [B, f`
      :host {
        display: block;
      }
      .bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 8px 12px;
        background: var(--card-background-color);
        border-top: 1px solid var(--divider-color);
        box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.15);
      }
      .timer {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 0 4px 0 12px;
        border-radius: 24px;
        border: 1px solid var(--divider-color);
        min-height: 48px;
      }
      .time {
        font-size: 1.3rem;
        font-variant-numeric: tabular-nums;
        font-weight: 500;
      }
      .label {
        max-width: 220px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.85rem;
      }
      .done {
        background: var(--warning-color, #ffa600);
        color: #000;
        animation: blink 1s steps(2, start) infinite;
      }
      @keyframes blink {
        to {
          opacity: 0.55;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .done {
          animation: none;
        }
      }
      .hint {
        width: 100%;
        --rb-icon-size: 18px;
      }
    `], customElements.get("rb-timer-bar") || customElements.define("rb-timer-bar", Je);
// src/i18n/de.ts
var U = {
	"app.title": "Rezeptbuch",
	"nav.recipes": "Rezepte",
	"nav.drafts": "Entwürfe",
	"nav.import": "Importieren",
	"nav.menu": "Menü",
	"common.back": "Zurück",
	"common.save": "Speichern",
	"common.cancel": "Abbrechen",
	"common.delete": "Löschen",
	"common.confirm_delete": "Wirklich löschen?",
	"common.loading": "Lädt …",
	"common.retry": "Erneut versuchen",
	"common.close": "Schließen",
	"common.minutes": "{n} Min.",
	"common.hours_minutes": "{h} Std. {m} Min.",
	"common.hours": "{h} Std.",
	"common.load_more": "Mehr laden",
	"common.error": "Fehler: {message}",
	"list.search": "Suchen …",
	"list.category": "Kategorie",
	"list.all_categories": "Alle Kategorien",
	"list.uncategorized": "Ohne Kategorie",
	"list.tag": "Tag",
	"list.all_tags": "Alle Tags",
	"list.sort": "Sortierung",
	"list.empty": "Keine Rezepte gefunden.",
	"list.count": "{n} Rezepte",
	"list.cooked": "{n}× gekocht",
	"sort.name": "Name",
	"sort.rating": "Bewertung",
	"sort.last_cooked": "Zuletzt gekocht",
	"sort.least_recently_cooked": "Lange nicht gekocht",
	"sort.new": "Neueste",
	"recipe.servings": "Portionen",
	"recipe.prep": "Vorbereitung",
	"recipe.cook": "Kochen/Backen",
	"recipe.total": "Gesamt",
	"recipe.ingredients": "Zutaten",
	"recipe.steps": "Zubereitung",
	"recipe.source": "Quelle",
	"recipe.version": "Version",
	"recipe.default": "Standard",
	"recipe.set_default": "Als Standard verwenden",
	"recipe.show_diff": "Unterschiede zum Original",
	"recipe.hide_diff": "Unterschiede ausblenden",
	"recipe.no_diff": "Keine Unterschiede zum Original.",
	"recipe.shopping": "Auf die Einkaufsliste",
	"recipe.shopping_done": "{n} Einträge auf der Einkaufsliste",
	"recipe.delete": "Rezept löschen",
	"recipe.deleted": "Rezept gelöscht",
	"recipe.notes": "Notizen",
	"recipe.add_note": "Notiz hinzufügen",
	"recipe.note_placeholder": "z. B. nächstes Mal weniger Salz",
	"recipe.ratings": "Bewertungen",
	"recipe.avg": "⌀ {stars} ({n} Bewertungen)",
	"recipe.no_ratings": "Noch keine Bewertungen.",
	"recipe.rate": "Bewerten",
	"recipe.cooked": "Heute gekocht",
	"recipe.comment": "Kommentar",
	"recipe.rated": "Bewertung gespeichert",
	"recipe.history": "Verlauf",
	"recipe.last_cooked": "Zuletzt gekocht: {date}",
	"recipe.never_cooked": "Noch nie gekocht",
	"recipe.categories": "Kategorien",
	"recipe.tags": "Tags",
	"recipe.choose_stars": "Bitte Sterne wählen oder „Heute gekocht“ ankreuzen.",
	"timer.start": "Timer {time}",
	"timer.pause": "Pause",
	"timer.resume": "Weiter",
	"timer.stop": "Beenden",
	"timer.done": "Fertig: {label}",
	"timer.no_sound": "Ton nicht möglich – bitte auf den Bildschirm achten.",
	"timer.dismiss": "OK",
	"timer.step": "Schritt {n}",
	"diff.added": "neu",
	"diff.removed": "gestrichen",
	"diff.changed": "geändert",
	"drafts.empty": "Keine offenen Entwürfe.",
	"drafts.from_url": "von URL",
	"drafts.from_photo": "vom Foto",
	"drafts.manual": "manuell",
	"drafts.open": "Prüfen",
	"draft.title": "Titel",
	"draft.description": "Beschreibung",
	"draft.servings": "Portionen",
	"draft.servings_unit": "Einheit (z. B. Portionen, Stück)",
	"draft.prep": "Vorbereitung (Min.)",
	"draft.cook": "Koch-/Backzeit (Min.)",
	"draft.total": "Gesamtzeit (Min.)",
	"draft.ingredients": "Zutaten – eine pro Zeile, Gruppen als „Name:“",
	"draft.steps": "Schritte – durch eine Leerzeile getrennt",
	"draft.categories": "Kategorien",
	"draft.tags": "Tags – durch Komma getrennt",
	"draft.image": "Rezeptbild",
	"draft.no_image": "Kein Bild",
	"draft.warnings": "Hinweise",
	"draft.similar": "Ähnliche Rezepte",
	"draft.save": "Entwurf speichern",
	"draft.saved": "Entwurf gespeichert",
	"draft.confirm": "Als Rezept übernehmen",
	"draft.discard": "Verwerfen",
	"draft.confirm_discard": "Wirklich verwerfen?",
	"draft.discarded": "Entwurf verworfen",
	"draft.duplicate": "Dieses Rezept gibt es schon.",
	"draft.save_anyway": "Trotzdem übernehmen",
	"draft.preview": "Vorschau",
	"import.title": "Rezept importieren",
	"import.tab_url": "URL",
	"import.tab_photo": "Foto",
	"import.url_label": "Adresse der Rezeptseite",
	"import.url_button": "Importieren",
	"import.working": "Wird importiert …",
	"import.duplicate": "Schon vorhanden: {title}",
	"import.open_existing": "Vorhandenes öffnen",
	"import.photo_hint": "Ein oder mehrere Fotos eines Rezepts, z. B. eine Doppelseite oder eine Karteikarte. Die Reihenfolge entspricht den Seiten.",
	"import.choose": "Fotos auswählen",
	"import.camera": "Kamera",
	"import.analyze": "Mit KI auswerten",
	"import.analyzing": "KI wertet die Fotos aus …",
	"import.no_ai": "Für den Foto-Import wird eine KI-Aufgabe (ai_task) benötigt. Bitte in Home Assistant einrichten.",
	"import.move_up": "Nach oben",
	"import.move_down": "Nach unten",
	"import.remove": "Entfernen",
	"import.page": "Seite {n}",
	"error.not_loaded": "Das Rezeptbuch ist nicht geladen.",
	"error.not_found": "Nicht gefunden.",
	"error.unauthorized": "Dafür sind Administratorrechte nötig.",
	"error.invalid_url": "Die Adresse ist ungültig.",
	"error.blocked_address": "Zugriff auf diese Adresse ist nicht erlaubt (lokales Netz).",
	"error.fetch_failed": "Die Seite konnte nicht abgerufen werden.",
	"error.response_too_large": "Die Seite ist zu groß.",
	"error.no_recipe_found": "Auf der Seite wurde kein Rezept gefunden.",
	"error.invalid_image": "Die Datei ist kein unterstütztes Bild.",
	"error.draft_not_found": "Der Entwurf existiert nicht mehr.",
	"error.duplicate_recipe": "Dieses Rezept gibt es schon.",
	"error.no_ai_task_entity": "Keine KI-Aufgabe (ai_task) verfügbar.",
	"error.ai_task_entity_not_found": "Die gewählte KI-Entität gibt es nicht mehr.",
	"error.ai_task_failed": "Die KI-Auswertung ist fehlgeschlagen.",
	"error.no_photos": "Bitte 1 bis 10 Fotos wählen.",
	"error.invalid_input": "Ungültige Eingabe.",
	"error.conflict": "Konflikt mit vorhandenen Daten.",
	"error.unknown_error": "Unbekannter Fehler."
}, Ye = {
	de: U,
	en: {
		"app.title": "Recipe book",
		"nav.recipes": "Recipes",
		"nav.drafts": "Drafts",
		"nav.import": "Import",
		"nav.menu": "Menu",
		"common.back": "Back",
		"common.save": "Save",
		"common.cancel": "Cancel",
		"common.delete": "Delete",
		"common.confirm_delete": "Really delete?",
		"common.loading": "Loading …",
		"common.retry": "Try again",
		"common.close": "Close",
		"common.minutes": "{n} min",
		"common.hours_minutes": "{h} h {m} min",
		"common.hours": "{h} h",
		"common.load_more": "Load more",
		"common.error": "Error: {message}",
		"list.search": "Search …",
		"list.category": "Category",
		"list.all_categories": "All categories",
		"list.uncategorized": "Uncategorized",
		"list.tag": "Tag",
		"list.all_tags": "All tags",
		"list.sort": "Sort",
		"list.empty": "No recipes found.",
		"list.count": "{n} recipes",
		"list.cooked": "cooked {n}×",
		"sort.name": "Name",
		"sort.rating": "Rating",
		"sort.last_cooked": "Last cooked",
		"sort.least_recently_cooked": "Not cooked for a while",
		"sort.new": "Newest",
		"recipe.servings": "Servings",
		"recipe.prep": "Preparation",
		"recipe.cook": "Cooking/baking",
		"recipe.total": "Total",
		"recipe.ingredients": "Ingredients",
		"recipe.steps": "Directions",
		"recipe.source": "Source",
		"recipe.version": "Version",
		"recipe.default": "Default",
		"recipe.set_default": "Use as default",
		"recipe.show_diff": "Differences to original",
		"recipe.hide_diff": "Hide differences",
		"recipe.no_diff": "No differences to the original.",
		"recipe.shopping": "Add to shopping list",
		"recipe.shopping_done": "{n} items on the shopping list",
		"recipe.delete": "Delete recipe",
		"recipe.deleted": "Recipe deleted",
		"recipe.notes": "Notes",
		"recipe.add_note": "Add note",
		"recipe.note_placeholder": "e.g. less salt next time",
		"recipe.ratings": "Ratings",
		"recipe.avg": "⌀ {stars} ({n} ratings)",
		"recipe.no_ratings": "No ratings yet.",
		"recipe.rate": "Rate",
		"recipe.cooked": "Cooked today",
		"recipe.comment": "Comment",
		"recipe.rated": "Rating saved",
		"recipe.history": "History",
		"recipe.last_cooked": "Last cooked: {date}",
		"recipe.never_cooked": "Never cooked",
		"recipe.categories": "Categories",
		"recipe.tags": "Tags",
		"recipe.choose_stars": "Please choose stars or tick “Cooked today”.",
		"timer.start": "Timer {time}",
		"timer.pause": "Pause",
		"timer.resume": "Resume",
		"timer.stop": "Stop",
		"timer.done": "Done: {label}",
		"timer.no_sound": "Sound not possible – please watch the screen.",
		"timer.dismiss": "OK",
		"timer.step": "Step {n}",
		"diff.added": "new",
		"diff.removed": "removed",
		"diff.changed": "changed",
		"drafts.empty": "No open drafts.",
		"drafts.from_url": "from URL",
		"drafts.from_photo": "from photo",
		"drafts.manual": "manual",
		"drafts.open": "Review",
		"draft.title": "Title",
		"draft.description": "Description",
		"draft.servings": "Servings",
		"draft.servings_unit": "Unit (e.g. servings, pieces)",
		"draft.prep": "Preparation (min)",
		"draft.cook": "Cooking/baking time (min)",
		"draft.total": "Total time (min)",
		"draft.ingredients": "Ingredients – one per line, groups as “Name:”",
		"draft.steps": "Steps – separated by a blank line",
		"draft.categories": "Categories",
		"draft.tags": "Tags – comma separated",
		"draft.image": "Recipe image",
		"draft.no_image": "No image",
		"draft.warnings": "Notes",
		"draft.similar": "Similar recipes",
		"draft.save": "Save draft",
		"draft.saved": "Draft saved",
		"draft.confirm": "Save as recipe",
		"draft.discard": "Discard",
		"draft.confirm_discard": "Really discard?",
		"draft.discarded": "Draft discarded",
		"draft.duplicate": "This recipe already exists.",
		"draft.save_anyway": "Save anyway",
		"draft.preview": "Preview",
		"import.title": "Import recipe",
		"import.tab_url": "URL",
		"import.tab_photo": "Photo",
		"import.url_label": "Address of the recipe page",
		"import.url_button": "Import",
		"import.working": "Importing …",
		"import.duplicate": "Already exists: {title}",
		"import.open_existing": "Open existing",
		"import.photo_hint": "One or more photos of a recipe, e.g. a double page or a recipe card. The order equals the pages.",
		"import.choose": "Choose photos",
		"import.camera": "Camera",
		"import.analyze": "Analyze with AI",
		"import.analyzing": "AI is analyzing the photos …",
		"import.no_ai": "Photo import requires an AI task (ai_task). Please set one up in Home Assistant.",
		"import.move_up": "Move up",
		"import.move_down": "Move down",
		"import.remove": "Remove",
		"import.page": "Page {n}",
		"error.not_loaded": "The recipe book is not loaded.",
		"error.not_found": "Not found.",
		"error.unauthorized": "Administrator rights are required.",
		"error.invalid_url": "The address is invalid.",
		"error.blocked_address": "Access to this address is not allowed (local network).",
		"error.fetch_failed": "The page could not be fetched.",
		"error.response_too_large": "The page is too large.",
		"error.no_recipe_found": "No recipe was found on the page.",
		"error.invalid_image": "The file is not a supported image.",
		"error.draft_not_found": "The draft no longer exists.",
		"error.duplicate_recipe": "This recipe already exists.",
		"error.no_ai_task_entity": "No AI task (ai_task) available.",
		"error.ai_task_entity_not_found": "The selected AI entity no longer exists.",
		"error.ai_task_failed": "The AI analysis failed.",
		"error.no_photos": "Please choose 1 to 10 photos.",
		"error.invalid_input": "Invalid input.",
		"error.conflict": "Conflict with existing data.",
		"error.unknown_error": "Unknown error."
	}
};
function Xe(e) {
	return (e ?? "").toLowerCase().startsWith("de") ? "de" : "en";
}
function Ze(e) {
	let t = Ye[Xe(e)];
	return (e, n) => {
		let r = t[e] ?? U[e] ?? e;
		if (n) for (let [e, t] of Object.entries(n)) r = r.split(`{${e}}`).join(String(t));
		return r;
	};
}
function W(e, t) {
	let n = `error.${t.code}`;
	return n in U ? e(n) : e("common.error", { message: t.message || t.code });
}
// src/router.ts
function Qe(e) {
	let t = (e ?? "").split("/").filter(Boolean), n = Number(t[1]);
	switch (t[0]) {
		case "rezept": return Number.isInteger(n) && n > 0 ? {
			view: "recipe",
			recipeId: n
		} : { view: "list" };
		case "entwuerfe": return { view: "drafts" };
		case "entwurf": return Number.isInteger(n) && n > 0 ? {
			view: "draft",
			draftId: n
		} : { view: "drafts" };
		case "import": return { view: "import" };
		default: return { view: "list" };
	}
}
function $e(e) {
	switch (e.view) {
		case "recipe": return `/rezept/${e.recipeId}`;
		case "drafts": return "/entwuerfe";
		case "draft": return `/entwurf/${e.draftId}`;
		case "import": return "/import";
		default: return "";
	}
}
function et(e, t, n = !1) {
	let r = `${e}${$e(t)}`;
	n ? history.replaceState(null, "", r) : history.pushState(null, "", r), window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: n } }));
}
// src/context.ts
function G(e, t = 0) {
	return e.flatMap((e) => [{
		category: e,
		depth: t
	}, ...G(e.children, t + 1)]);
}
// src/views/draft-editor.ts
var K;
function tt(e) {
	let t = e.version;
	return {
		title: e.title,
		description: e.description,
		servings: t.servings ? String(t.servings) : "",
		servings_unit: t.servings_unit ?? "",
		prep_time: t.prep_time ? String(t.prep_time) : "",
		cook_time: t.cook_time ? String(t.cook_time) : "",
		total_time: t.total_time ? String(t.total_time) : "",
		ingredients: e.ingredient_lines.join("\n"),
		steps: e.step_lines.join("\n\n"),
		tags: e.tags.join(", "),
		category_ids: [...e.category_ids],
		image: e.image
	};
}
var q = (e) => e.trim() ? Number(e.replace(",", ".")) : null, nt = class extends I {
	constructor() {
		super(), this._draft = null, this._form = null, this._tree = null, this._error = "", this._busy = !1, this._duplicate = !1, this._confirmDiscard = !1;
	}
	updated(e) {
		e.has("draftId") && this.load();
	}
	async load() {
		this._error = "";
		try {
			let [e, t] = await Promise.all([this.ctx.api.draft(this.draftId), this.ctx.api.categories()]);
			this._draft = e, this._form = tt(e), this._tree = t;
		} catch (e) {
			this._error = W(this.ctx.t, this.ctx.fail(e));
		}
	}
	set(e, t) {
		this._form &&= {
			...this._form,
			[e]: t
		};
	}
	async save() {
		let e = this._form;
		if (!e) return !1;
		try {
			let t = await this.ctx.api.updateDraft(this.draftId, {
				title: e.title.trim(),
				description: e.description.trim(),
				servings: q(e.servings),
				servings_unit: e.servings_unit.trim() || null,
				prep_time: q(e.prep_time),
				cook_time: q(e.cook_time),
				total_time: q(e.total_time),
				ingredient_lines: We(e.ingredients),
				step_lines: Ue(e.steps),
				tags: Ge(e.tags),
				category_ids: e.category_ids,
				image: e.image
			});
			return this._draft = t, this._form = tt(t), !0;
		} catch (e) {
			return this.ctx.toast(W(this.ctx.t, this.ctx.fail(e))), !1;
		}
	}
	async onSave() {
		this._busy = !0, await this.save() && this.ctx.toast(this.ctx.t("draft.saved")), this._busy = !1;
	}
	async onConfirm(e = !1) {
		this._busy = !0;
		try {
			if (!await this.save()) return;
			let t = await this.ctx.api.confirmDraft(this.draftId, e);
			this.ctx.go({
				view: "recipe",
				recipeId: t.recipe_id
			});
		} catch (e) {
			let t = this.ctx.fail(e);
			t.code === "duplicate_recipe" ? this._duplicate = !0 : this.ctx.toast(W(this.ctx.t, t));
		} finally {
			this._busy = !1;
		}
	}
	async onDiscard() {
		if (!this._confirmDiscard) this._confirmDiscard = !0, setTimeout(() => this._confirmDiscard = !1, 4e3);
		else {
			this._busy = !0;
			try {
				await this.ctx.api.discardDraft(this.draftId), this.ctx.toast(this.ctx.t("draft.discarded")), this.ctx.go({ view: "drafts" });
			} catch (e) {
				this.ctx.toast(W(this.ctx.t, this.ctx.fail(e)));
			} finally {
				this._busy = !1;
			}
		}
	}
	render() {
		let { t } = this.ctx;
		if (this._error) return D`<p class="error">${this._error}</p>`;
		let n = this._draft, i = this._form;
		if (!n || !i) return D`<p class="muted">${t("common.loading")}</p>`;
		let a = (e) => e.target.value;
		return D`
      <div class="top">
        <button class="icon" aria-label=${t("common.back")} @click=${() => this.ctx.go({ view: "drafts" })}>
          <rb-icon .path=${e}></rb-icon>
        </button>
        <h1>${i.title || "–"}</h1>
      </div>
      ${n.warnings.length ? D`<div class="warning">
            <strong>${t("draft.warnings")}</strong>
            <ul>
              ${n.warnings.map((e) => D`<li>${e}</li>`)}
            </ul>
          </div>` : k}
      ${n.similar_recipes.length ? D`<p class="row">
            ${t("draft.similar")}:
            ${n.similar_recipes.map((e) => D`<button @click=${() => this.ctx.go({
			view: "recipe",
			recipeId: e.id
		})}>${e.title}</button>`)}
          </p>` : k}
      <div class="layout">
        <div class="card">
          <label for="title">${t("draft.title")}</label>
          <input id="title" .value=${i.title} @input=${(e) => this.set("title", a(e))} />
          <label for="desc">${t("draft.description")}</label>
          <input id="desc" .value=${i.description} @input=${(e) => this.set("description", a(e))} />
          <div class="nums">
            ${[
			["servings", "draft.servings"],
			["prep_time", "draft.prep"],
			["cook_time", "draft.cook"],
			["total_time", "draft.total"]
		].map(([e, n]) => D`<div>
                  <label for=${e}>${t(n)}</label>
                  <input
                    id=${e}
                    inputmode="decimal"
                    .value=${i[e]}
                    @input=${(t) => this.set(e, a(t))}
                  />
                </div>`)}
            <div>
              <label for="unit">${t("draft.servings_unit")}</label>
              <input id="unit" .value=${i.servings_unit} @input=${(e) => this.set("servings_unit", a(e))} />
            </div>
          </div>
          <label for="ing">${t("draft.ingredients")}</label>
          <textarea
            id="ing"
            class="ing"
            .value=${i.ingredients}
            @input=${(e) => this.set("ingredients", a(e))}
          ></textarea>
        </div>
        <div class="card">
          <label for="steps">${t("draft.steps")}</label>
          <textarea
            id="steps"
            class="steps"
            .value=${i.steps}
            @input=${(e) => this.set("steps", a(e))}
          ></textarea>
          ${this.renderCategories(i)}
          <label for="tags">${t("draft.tags")}</label>
          <input id="tags" .value=${i.tags} @input=${(e) => this.set("tags", a(e))} />
          ${this.renderImages(n, i)}
        </div>
      </div>
      <div class="actions">
        ${this._duplicate ? D`<span class="warning grow">${t("draft.duplicate")}</span>
              <button ?disabled=${this._busy} @click=${() => this.onConfirm(!0)}>${t("draft.save_anyway")}</button>` : k}
        <button class="danger" ?disabled=${this._busy} @click=${this.onDiscard}>
          <rb-icon .path=${r}></rb-icon>${this._confirmDiscard ? t("draft.confirm_discard") : t("draft.discard")}
        </button>
        <button ?disabled=${this._busy} @click=${this.onSave}>${t("draft.save")}</button>
        <button class="primary" ?disabled=${this._busy || !i.title.trim()} @click=${() => this.onConfirm()}>
          <rb-icon .path=${"M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"}></rb-icon>${t("draft.confirm")}
        </button>
      </div>
    `;
	}
	renderCategories(e) {
		let { t } = this.ctx, n = this._tree ? G(this._tree.categories) : [];
		return D`<label>${t("draft.categories")}</label>
      <div class="cats">
        ${n.map(({ category: t, depth: n }) => D`<label style=${`padding-left:${n * 20}px`}>
              <input
                type="checkbox"
                .checked=${e.category_ids.includes(t.id)}
                @change=${(n) => {
			let r = n.target.checked, i = e.category_ids.filter((e) => e !== t.id);
			this.set("category_ids", r ? [...i, t.id] : i);
		}}
              />
              ${t.name}
            </label>`)}
      </div>`;
	}
	renderImages(e, t) {
		let { t: n } = this.ctx;
		return e.images.length ? D`<label>${n("draft.image")}</label>
      <div class="images">
        <label>
          <span style="width:110px;height:110px;display:flex;align-items:center;justify-content:center" class="muted"
            >${n("draft.no_image")}</span
          >
          <input type="radio" name="img" .checked=${!t.image} @change=${() => this.set("image", null)} />
        </label>
        ${e.images.map((e) => D`<label>
              ${e.url ? D`<img src=${e.url} alt="" />` : k}
              <input
                type="radio"
                name="img"
                .checked=${t.image === e.path}
                @change=${() => this.set("image", e.path)}
              />
            </label>`)}
      </div>` : k;
	}
};
K = nt, K.properties = {
	ctx: { attribute: !1 },
	draftId: { type: Number },
	_draft: { state: !0 },
	_form: { state: !0 },
	_tree: { state: !0 },
	_error: { state: !0 },
	_busy: { state: !0 },
	_duplicate: { state: !0 },
	_confirmDiscard: { state: !0 }
}, K.styles = [B, f`
      .top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
      }
      .top h1 {
        flex: 1;
        margin: 0;
      }
      .layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        align-items: start;
      }
      @media (max-width: 860px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
      .nums {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 0 8px;
      }
      textarea.ing {
        min-height: 260px;
      }
      textarea.steps {
        min-height: 320px;
      }
      .cats {
        max-height: 260px;
        overflow: auto;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 4px 8px;
      }
      .cats label {
        display: flex;
        align-items: center;
        gap: 8px;
        min-height: 40px;
        margin: 0;
        color: var(--primary-text-color);
        font-size: 1rem;
      }
      .cats input,
      .images input {
        width: 22px;
        min-height: 22px;
      }
      .images {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .images label {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        margin: 0;
      }
      .images img {
        width: 110px;
        height: 110px;
        object-fit: cover;
        border-radius: 8px;
      }
      .actions {
        position: sticky;
        bottom: 0;
        padding: 12px 0;
        background: var(--primary-background-color);
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
      }
      .warning ul {
        margin: 4px 0 0;
        padding-left: 1.2em;
      }
    `], customElements.get("rb-draft-editor") || customElements.define("rb-draft-editor", nt);
// src/views/drafts-view.ts
var J, rt = class extends I {
	constructor() {
		super(), this._drafts = [], this._error = "", this._loaded = !1;
	}
	connectedCallback() {
		super.connectedCallback(), this.load();
	}
	async load() {
		try {
			this._drafts = (await this.ctx.api.drafts()).drafts;
		} catch (e) {
			this._error = W(this.ctx.t, this.ctx.fail(e));
		} finally {
			this._loaded = !0;
		}
	}
	render() {
		let { t: e, language: t } = this.ctx;
		if (this._error) return D`<p class="error">${this._error}</p>`;
		if (!this._loaded) return D`<p class="muted">${e("common.loading")}</p>`;
		if (!this._drafts.length) return D`<p class="muted">${e("drafts.empty")}</p>`;
		let n = {
			url: e("drafts.from_url"),
			photo: e("drafts.from_photo"),
			manual: e("drafts.manual")
		};
		return D`<div class="list">
      ${this._drafts.map((r) => {
			let a = r.images.find((e) => e.path === r.image) ?? r.images[0];
			return D`<div class="card item">
          ${a?.url ? D`<img src=${a.url} alt="" loading="lazy" />` : D`<span class="ph"><rb-icon .path=${i}></rb-icon></span>`}
          <div class="grow">
            <div><strong>${r.title || "–"}</strong></div>
            <div class="muted row">
              <span>${n[r.source_type]} · ${z(t, r.created)}</span>
              ${r.warnings.length ? D`<span class="row warn"><rb-icon .path=${"M12,2L1,21H23M12,6L19.53,19H4.47M11,10V14H13V10M11,16V18H13V16"}></rb-icon>${r.warnings.length}</span>` : k}
            </div>
          </div>
          <button class="primary" @click=${() => this.ctx.go({
				view: "draft",
				draftId: r.id
			})}>
            ${e("drafts.open")}
          </button>
        </div>`;
		})}
    </div>`;
	}
};
J = rt, J.properties = {
	ctx: { attribute: !1 },
	_drafts: { state: !0 },
	_error: { state: !0 },
	_loaded: { state: !0 }
}, J.styles = [B, f`
      .list {
        display: grid;
        gap: 10px;
      }
      .item {
        display: flex;
        gap: 12px;
        align-items: center;
      }
      .item img,
      .ph {
        width: 72px;
        height: 72px;
        object-fit: cover;
        border-radius: 8px;
        flex: none;
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .warn {
        color: var(--warning-color, #ffa600);
        --rb-icon-size: 18px;
      }
    `], customElements.get("rb-drafts-view") || customElements.define("rb-drafts-view", rt);
// src/image.ts
var it = 2400;
function at(e, t, n = it) {
	let r = Math.max(e, t);
	if (r <= n) return [e, t];
	let i = n / r;
	return [Math.round(e * i), Math.round(t * i)];
}
async function ot(e) {
	try {
		let t = await createImageBitmap(e, { imageOrientation: "from-image" }), [n, r] = at(t.width, t.height), i = document.createElement("canvas");
		i.width = n, i.height = r;
		let a = i.getContext("2d");
		return a ? (a.drawImage(t, 0, 0, n, r), t.close(), await new Promise((e) => i.toBlob(e, "image/jpeg", .85)) ?? e) : e;
	} catch {
		return e;
	}
}
// src/views/import-view.ts
var Y, st = class extends I {
	constructor() {
		super(), this._tab = "url", this._url = "", this._photos = [], this._busy = !1, this._error = "", this._duplicate = null;
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._photos.forEach((e) => URL.revokeObjectURL(e.url));
	}
	async importUrl(e = !1) {
		this._busy = !0, this._error = "", this._duplicate = null;
		try {
			let t = await this.ctx.api.importUrl(this._url.trim(), e);
			t.status === "duplicate" ? this._duplicate = {
				recipe_id: t.recipe_id,
				title: t.title
			} : this.ctx.go({
				view: "draft",
				draftId: t.draft.id
			});
		} catch (e) {
			this._error = W(this.ctx.t, this.ctx.fail(e));
		} finally {
			this._busy = !1;
		}
	}
	addFiles(e) {
		let t = e.target, n = Array.from(t.files ?? []).filter((e) => e.type.startsWith("image/") || !e.type);
		this._photos = [...this._photos, ...n.map((e) => ({
			file: e,
			url: URL.createObjectURL(e)
		}))].slice(0, 10), t.value = "";
	}
	move(e, t) {
		let n = [...this._photos], r = e + t;
		r < 0 || r >= n.length || ([n[e], n[r]] = [n[r], n[e]], this._photos = n);
	}
	removePhoto(e) {
		URL.revokeObjectURL(this._photos[e].url), this._photos = this._photos.filter((t, n) => n !== e);
	}
	async analyze() {
		this._busy = !0, this._error = "";
		try {
			let e = await Promise.all(this._photos.map((e) => ot(e.file))), t = await this.ctx.api.uploadPhotos(e);
			t.status === "draft" && this.ctx.go({
				view: "draft",
				draftId: t.draft.id
			});
		} catch (e) {
			this._error = W(this.ctx.t, this.ctx.fail(e));
		} finally {
			this._busy = !1;
		}
	}
	render() {
		let { t: e } = this.ctx;
		return D`
      <h1>${e("import.title")}</h1>
      <div class="tabs" role="tablist">
        <button role="tab" aria-selected=${this._tab === "url"} @click=${() => this._tab = "url"}>
          <rb-icon .path=${"M3.9,12C3.9,10.29 5.29,8.9 7,8.9H11V7H7A5,5 0 0,0 2,12A5,5 0 0,0 7,17H11V15.1H7C5.29,15.1 3.9,13.71 3.9,12M8,13H16V11H8V13M17,7H13V8.9H17C18.71,8.9 20.1,10.29 20.1,12C20.1,13.71 18.71,15.1 17,15.1H13V17H17A5,5 0 0,0 22,12A5,5 0 0,0 17,7Z"}></rb-icon>${e("import.tab_url")}
        </button>
        <button role="tab" aria-selected=${this._tab === "photo"} @click=${() => this._tab = "photo"}>
          <rb-icon .path=${t}></rb-icon>${e("import.tab_photo")}
        </button>
      </div>
      <div class="card">${this._tab === "url" ? this.renderUrl() : this.renderPhoto()}</div>
      ${this._error ? D`<p class="error">${this._error}</p>` : k}
    `;
	}
	renderUrl() {
		let { t: e } = this.ctx;
		return D`<label for="url">${e("import.url_label")}</label>
      <div class="row">
        <input
          id="url"
          class="grow"
          type="url"
          inputmode="url"
          autocomplete="off"
          placeholder="https://…"
          .value=${this._url}
          @input=${(e) => this._url = e.target.value}
          @keydown=${(e) => e.key === "Enter" && this._url.trim() && this.importUrl()}
        />
        <button class="primary" ?disabled=${this._busy || !this._url.trim()} @click=${() => this.importUrl()}>
          ${this._busy ? e("import.working") : e("import.url_button")}
        </button>
      </div>
      ${this._duplicate ? D`<p class="warning row">
            <span class="grow">${e("import.duplicate", { title: this._duplicate.title })}</span>
            <button @click=${() => this.ctx.go({
			view: "recipe",
			recipeId: this._duplicate.recipe_id
		})}>
              ${e("import.open_existing")}
            </button>
            <button @click=${() => this.importUrl(!0)}>${e("draft.save_anyway")}</button>
          </p>` : k}`;
	}
	renderPhoto() {
		let { t: e } = this.ctx;
		return this.ctx.info && !this.ctx.info.ai_task_available ? D`<p class="warning">${e("import.no_ai")}</p>` : D`<p class="muted">${e("import.photo_hint")}</p>
      <div class="row">
        <label class="btn" for="files"><rb-icon .path=${"M18 15V18H15V20H18V23H20V20H23V18H20V15H18M13.3 21H5C3.9 21 3 20.1 3 19V5C3 3.9 3.9 3 5 3H19C20.1 3 21 3.9 21 5V13.3C20.4 13.1 19.7 13 19 13C17.9 13 16.8 13.3 15.9 13.9L14.5 12L11 16.5L8.5 13.5L5 18H13.1C13 18.3 13 18.7 13 19C13 19.7 13.1 20.4 13.3 21Z"}></rb-icon>${e("import.choose")}</label>
        <input id="files" type="file" accept="image/*" multiple @change=${this.addFiles} />
        <label class="btn" for="camera"><rb-icon .path=${t}></rb-icon>${e("import.camera")}</label>
        <input id="camera" type="file" accept="image/*" capture="environment" @change=${this.addFiles} />
      </div>
      <div class="pages">
        ${this._photos.map((t, r) => D`<div class="page">
            <img src=${t.url} alt=${e("import.page", { n: r + 1 })} />
            <div class="tools">
              <button class="icon" aria-label=${e("import.move_up")} ?disabled=${r === 0} @click=${() => this.move(r, -1)}>
                <rb-icon .path=${"M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z"}></rb-icon>
              </button>
              <span class="muted" style="align-self:center">${e("import.page", { n: r + 1 })}</span>
              <button
                class="icon"
                aria-label=${e("import.move_down")}
                ?disabled=${r === this._photos.length - 1}
                @click=${() => this.move(r, 1)}
              >
                <rb-icon .path=${"M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z"}></rb-icon>
              </button>
              <button class="icon" aria-label=${e("import.remove")} @click=${() => this.removePhoto(r)}>
                <rb-icon .path=${n}></rb-icon>
              </button>
            </div>
          </div>`)}
      </div>
      <button class="primary" ?disabled=${this._busy || !this._photos.length} @click=${this.analyze}>
        ${this._busy ? e("import.analyzing") : e("import.analyze")}
      </button>`;
	}
};
Y = st, Y.properties = {
	ctx: { attribute: !1 },
	_tab: { state: !0 },
	_url: { state: !0 },
	_photos: { state: !0 },
	_busy: { state: !0 },
	_error: { state: !0 },
	_duplicate: { state: !0 }
}, Y.styles = [B, f`
      .tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      .tabs button[aria-selected="true"] {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        border-color: var(--primary-color);
      }
      .pages {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 10px;
        margin: 12px 0;
      }
      .page {
        position: relative;
      }
      .page img {
        width: 100%;
        aspect-ratio: 3 / 4;
        object-fit: cover;
        border-radius: 8px;
        display: block;
      }
      .page .tools {
        display: flex;
        justify-content: space-between;
      }
      input[type="file"] {
        display: none;
      }
      .card {
        max-width: 900px;
      }
    `], customElements.get("rb-import-view") || customElements.define("rb-import-view", st);
// src/components/rb-stars.ts
var X, ct = class extends I {
	constructor() {
		super(), this.value = null, this.editable = !1, this.label = "";
	}
	pick(e) {
		this.value = e, this.dispatchEvent(new CustomEvent("change", {
			detail: e,
			bubbles: !0,
			composed: !0
		}));
	}
	render() {
		let e = this.value ?? 0;
		return D`${[
			1,
			2,
			3,
			4,
			5
		].map((t) => D`<span class="star"
        ><rb-icon .path=${e >= t ? "M12,17.27L18.18,21L16.54,13.97L22,9.24L14.81,8.62L12,2L9.19,8.62L2,9.24L7.45,13.97L5.82,21L12,17.27Z" : e >= t - .5 ? "M12,15.4V6.1L13.71,10.13L18.09,10.5L14.77,13.39L15.76,17.67M22,9.24L14.81,8.63L12,2L9.19,8.63L2,9.24L7.45,13.97L5.82,21L12,17.27L18.18,21L16.54,13.97L22,9.24Z" : "M12,15.39L8.24,17.66L9.23,13.38L5.91,10.5L10.29,10.13L12,6.09L13.71,10.13L18.09,10.5L14.77,13.38L15.76,17.66M22,9.24L14.81,8.63L12,2L9.19,8.63L2,9.24L7.45,13.97L5.82,21L12,17.27L18.18,21L16.54,13.97L22,9.24Z"}></rb-icon>
        ${this.editable ? D`<button class="left" aria-label=${`${t - .5}`} @click=${() => this.pick(t - .5)}></button
              ><button class="right" aria-label=${`${t}`} @click=${() => this.pick(t)}></button>` : k}</span
      >`)}`;
	}
};
X = ct, X.properties = {
	value: { type: Number },
	editable: { type: Boolean },
	label: { type: String }
}, X.styles = f`
    :host {
      display: inline-flex;
      color: var(--rb-star-color, #f5a623);
      --rb-icon-size: var(--rb-star-size, 20px);
    }
    .star {
      position: relative;
      display: inline-flex;
    }
    button {
      all: unset;
      position: absolute;
      top: -10px;
      bottom: -10px;
      width: 50%;
      cursor: pointer;
    }
    button.left {
      left: 0;
    }
    button.right {
      right: 0;
    }
    button:focus-visible {
      outline: 2px solid var(--primary-color);
    }
  `, customElements.get("rb-stars") || customElements.define("rb-stars", ct);
// src/views/recipe-list.ts
var Z, lt = 60, Q = {
	query: "",
	category: "",
	tag: "",
	sort: "name"
}, ut = class extends I {
	constructor() {
		super(), this._items = [], this._total = 0, this._tree = null, this._tags = [], this._loading = !1, this._error = "";
	}
	connectedCallback() {
		super.connectedCallback(), this.loadMeta(), this.load(!0);
	}
	async loadMeta() {
		try {
			let [e, t] = await Promise.all([this.ctx.api.categories(), this.ctx.api.tags()]);
			this._tree = e, this._tags = t.tags;
		} catch (e) {
			this._error = W(this.ctx.t, this.ctx.fail(e));
		}
	}
	async load(e) {
		this._loading = !0, this._error = "";
		let t = Q.category;
		try {
			let n = await this.ctx.api.list({
				query: Q.query || void 0,
				category_id: t && t !== "none" ? Number(t) : void 0,
				uncategorized: t === "none",
				tags: Q.tag ? [Q.tag] : [],
				sort: Q.query && Q.sort === "name" ? "relevance" : Q.sort,
				limit: lt,
				offset: e ? 0 : this._items.length
			});
			this._items = e ? n.items : [...this._items, ...n.items], this._total = n.total;
		} catch (e) {
			this._error = W(this.ctx.t, this.ctx.fail(e));
		} finally {
			this._loading = !1;
		}
	}
	setFilter(e, t, n = !1) {
		Q[e] = t, clearTimeout(this._timer), n ? this._timer = setTimeout(() => void this.load(!0), 300) : this.load(!0);
	}
	render() {
		let { t: e } = this.ctx, t = this._tree ? G(this._tree.categories) : [];
		return D`
      <div class="filters">
        <div class="search">
          <rb-icon .path=${"M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"}></rb-icon>
          <input
            type="search"
            .value=${Q.query}
            placeholder=${e("list.search")}
            aria-label=${e("list.search")}
            @input=${(e) => this.setFilter("query", e.target.value, !0)}
          />
        </div>
        <select
          aria-label=${e("list.category")}
          @change=${(e) => this.setFilter("category", e.target.value)}
        >
          <option value="" ?selected=${!Q.category}>${e("list.all_categories")}</option>
          ${t.map(({ category: e, depth: t }) => D`<option value=${String(e.id)} ?selected=${Q.category === String(e.id)}>
                ${" ".repeat(t)}${e.name} (${e.count_total})
              </option>`)}
          <option value="none" ?selected=${Q.category === "none"}>
            ${e("list.uncategorized")} (${this._tree?.uncategorized ?? 0})
          </option>
        </select>
        <select
          aria-label=${e("list.tag")}
          @change=${(e) => this.setFilter("tag", e.target.value)}
        >
          <option value="" ?selected=${!Q.tag}>${e("list.all_tags")}</option>
          ${this._tags.map((e) => D`<option value=${e.name} ?selected=${Q.tag === e.name}>${e.name}</option>`)}
        </select>
        <select
          aria-label=${e("list.sort")}
          @change=${(e) => this.setFilter("sort", e.target.value)}
        >
          ${[
			"name",
			"rating",
			"last_cooked",
			"least_recently_cooked",
			"new"
		].map((t) => D`<option value=${t} ?selected=${Q.sort === t}>${e(`sort.${t}`)}</option>`)}
        </select>
      </div>
      ${this._error ? D`<p class="error">${this._error}</p>` : k}
      <p class="muted">${e("list.count", { n: this._total })}</p>
      ${!this._loading && !this._items.length ? D`<p class="muted">${e("list.empty")}</p>` : k}
      <div class="grid">${this._items.map((e) => this.renderTile(e))}</div>
      ${this._items.length < this._total ? D`<div class="more">
            <button ?disabled=${this._loading} @click=${() => this.load(!1)}>${e("common.load_more")}</button>
          </div>` : k}
      ${this._loading ? D`<p class="muted">${e("common.loading")}</p>` : k}
    `;
	}
	renderTile(e) {
		let { t } = this.ctx, n = R(t, e.total_time);
		return D`<a
      class="tile"
      href=${`${this.ctx.prefix}/rezept/${e.recipe_id}`}
      @click=${(t) => {
			t.ctrlKey || t.metaKey || t.button !== 0 || (t.preventDefault(), this.ctx.go({
				view: "recipe",
				recipeId: e.recipe_id
			}));
		}}
    >
      <div class="thumb">
        ${e.image_url ? D`<img src=${e.image_url} alt="" loading="lazy" />` : D`<rb-icon .path=${"M11,9H9V2H7V9H5V2H3V9C3,11.12 4.66,12.84 6.75,12.97V22H9.25V12.97C11.34,12.84 13,11.12 13,9V2H11V9M16,6V14H18.5V22H21V2C18.24,2 16,4.24 16,6Z"}></rb-icon>`}
      </div>
      <div class="body">
        <span class="title">${e.title}</span>
        <span class="meta row muted">
          ${e.avg_stars === null ? k : D`<rb-stars .value=${e.avg_stars}></rb-stars>`}
          ${n ? D`<span class="row"><rb-icon .path=${"M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z"}></rb-icon>${n}</span>` : k}
          ${e.cooked_count ? D`<span>${t("list.cooked", { n: e.cooked_count })}</span>` : k}
        </span>
      </div>
    </a>`;
	}
};
Z = ut, Z.properties = {
	ctx: { attribute: !1 },
	_items: { state: !0 },
	_total: { state: !0 },
	_tree: { state: !0 },
	_tags: { state: !0 },
	_loading: { state: !0 },
	_error: { state: !0 }
}, Z.styles = [B, f`
      .filters {
        display: grid;
        grid-template-columns: 2fr 1.4fr 1fr 1fr;
        gap: 8px;
        margin-bottom: 16px;
      }
      @media (max-width: 800px) {
        .filters {
          grid-template-columns: 1fr 1fr;
        }
        .search {
          grid-column: 1 / -1;
        }
      }
      .search {
        position: relative;
      }
      .search rb-icon {
        position: absolute;
        left: 10px;
        top: 10px;
        color: var(--secondary-text-color);
      }
      .search input {
        padding-left: 40px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
      }
      a.tile {
        display: flex;
        flex-direction: column;
        color: inherit;
        text-decoration: none;
        background: var(--card-background-color);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0, 0, 0, 0.2));
        overflow: hidden;
        min-height: 44px;
      }
      .thumb {
        aspect-ratio: 4 / 3;
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--secondary-text-color);
        --rb-icon-size: 48px;
      }
      .thumb img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .body {
        padding: 10px 12px 12px;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .title {
        font-weight: 500;
        line-height: 1.3;
      }
      .meta {
        font-size: 0.85rem;
        --rb-icon-size: 16px;
        --rb-star-size: 16px;
      }
      .more {
        display: flex;
        justify-content: center;
        margin: 16px 0;
      }
    `], customElements.get("rb-recipe-list") || customElements.define("rb-recipe-list", ut);
// src/views/diff-view.ts
var $, dt = class extends I {
	render() {
		let e = this.diff, { t } = this.ctx;
		if (!e) return k;
		if (!e.has_changes) return D`<p class="muted">${t("recipe.no_diff")}</p>`;
		let n = (e) => e === "unchanged" ? k : D`<span class="badge">${t(`diff.${e}`)}</span>`;
		return D`
      ${e.meta.length ? D`<ul>
            ${e.meta.map((e) => D`<li class="changed">${e.label}: ${e.old ?? "–"} → ${e.new ?? "–"}</li>`)}
          </ul>` : k}
      <h3>${t("recipe.ingredients")}</h3>
      <ul>
        ${e.ingredients.filter((e) => e.status !== "unchanged").map((e) => D`<li class=${e.status}>
                ${n(e.status)}${e.summary || (e.new ?? e.old)?.name}
              </li>`)}
      </ul>
      <h3>${t("recipe.steps")}</h3>
      <ul>
        ${e.steps.filter((e) => e.status !== "unchanged").map((e) => D`<li class=${e.status}>
                ${n(e.status)}
                ${e.words && e.words.length ? e.words.map((e) => e.op === "insert" ? D`<ins>${e.text}</ins>` : e.op === "delete" ? D`<del>${e.text}</del>` : e.text) : (e.new ?? e.old)?.text}
              </li>`)}
      </ul>
    `;
	}
};
$ = dt, $.properties = {
	ctx: { attribute: !1 },
	diff: { attribute: !1 }
}, $.styles = [B, f`
      ul {
        list-style: none;
        padding: 0;
        margin: 0 0 12px;
      }
      li {
        padding: 6px 8px;
        border-radius: 6px;
        margin-bottom: 4px;
      }
      .added,
      ins {
        background: color-mix(in srgb, var(--success-color, #43a047) 20%, transparent);
        text-decoration: none;
      }
      .removed,
      del {
        background: color-mix(in srgb, var(--error-color, #db4437) 16%, transparent);
        text-decoration: line-through;
      }
      .changed {
        background: color-mix(in srgb, var(--warning-color, #ffa600) 20%, transparent);
      }
      .badge {
        font-size: 0.75rem;
        text-transform: uppercase;
        margin-right: 6px;
        opacity: 0.8;
      }
    `], customElements.get("rb-diff") || customElements.define("rb-diff", dt);
// src/views/recipe-view.ts
var ft, pt = class extends I {
	constructor() {
		super(), this.addToShopping = () => {
			let e = this._recipe;
			e && this.run(async () => {
				let t = await this.ctx.api.addToShoppingList(e.id, this._servings);
				this.ctx.toast(this.ctx.t("recipe.shopping_done", { n: t.items.length }));
			});
		}, this.deleteRecipe = () => {
			let e = this._recipe;
			e && (this._confirmDelete ? this.run(async () => {
				await this.ctx.api.deleteRecipe(e.id), this.ctx.go({ view: "list" });
			}, this.ctx.t("recipe.deleted")) : (this._confirmDelete = !0, setTimeout(() => this._confirmDelete = !1, 4e3)));
		}, this._recipe = null, this._versionId = null, this._servings = null, this._checked = /* @__PURE__ */ new Set(), this._diff = null, this._showDiff = !1, this._error = "", this._stars = null, this._cooked = !0, this._comment = "", this._note = "", this._confirmDelete = !1, this._busy = !1;
	}
	updated(e) {
		e.has("recipeId") && (this._versionId = null, this._servings = null, this._checked = /* @__PURE__ */ new Set(), this._showDiff = !1, this.load());
	}
	async load() {
		this._error = "";
		try {
			this._recipe = await this.ctx.api.recipe(this.recipeId, this._versionId, this._servings), this._showDiff && await this.loadDiff();
		} catch (e) {
			this._error = W(this.ctx.t, this.ctx.fail(e));
		}
	}
	async loadDiff() {
		let e = this._recipe, t = e?.versions.find((e) => e.is_original);
		e && t && (this._diff = await this.ctx.api.diff(t.id, e.version.id));
	}
	changeServings(e) {
		let t = this._recipe;
		if (!t) return;
		let n = t.version.data.servings ?? t.version.original_servings ?? 1, r = Math.max(.5, Math.min(500, n + e * (n < 2 ? .5 : 1)));
		this.setServings(r);
	}
	setServings(e) {
		!Number.isFinite(e) || e <= 0 || (this._servings = e, this.load());
	}
	toggle(e) {
		let t = new Set(this._checked);
		t.has(e) ? t.delete(e) : t.add(e), this._checked = t;
	}
	async run(e, t) {
		this._busy = !0;
		try {
			await e(), t && this.ctx.toast(t);
		} catch (e) {
			this.ctx.toast(W(this.ctx.t, this.ctx.fail(e)));
		} finally {
			this._busy = !1;
		}
	}
	render() {
		let { t } = this.ctx;
		if (this._error) return D`<p class="error">${this._error}</p>
        <button @click=${() => this.load()}>${t("common.retry")}</button>`;
		let n = this._recipe;
		if (!n) return D`<p class="muted">${t("common.loading")}</p>`;
		let i = n.version.data;
		return D`
      <div class="top">
        <button class="icon" aria-label=${t("common.back")} @click=${() => this.ctx.go({ view: "list" })}>
          <rb-icon .path=${e}></rb-icon>
        </button>
        <h1>${n.title}</h1>
        <button ?disabled=${this._busy} @click=${this.addToShopping}>
          <rb-icon .path=${"M11 9H13V6H16V4H13V1H11V4H8V6H11M7 18C5.9 18 5 18.9 5 20S5.9 22 7 22 9 21.1 9 20 8.1 18 7 18M17 18C15.9 18 15 18.9 15 20S15.9 22 17 22 19 21.1 19 20 18.1 18 17 18M7.2 14.8V14.7L8.1 13H15.5C16.2 13 16.9 12.6 17.2 12L21.1 5L19.4 4L15.5 11H8.5L4.3 2H1V4H3L6.6 11.6L5.2 14C5.1 14.3 5 14.6 5 15C5 16.1 5.9 17 7 17H19V15H7.4C7.3 15 7.2 14.9 7.2 14.8Z"}></rb-icon><span>${t("recipe.shopping")}</span>
        </button>
        ${this.ctx.info?.is_admin ? D`<button
              class="danger"
              ?disabled=${this._busy}
              @click=${this.deleteRecipe}
              aria-label=${t("recipe.delete")}
            >
              <rb-icon .path=${r}></rb-icon>${this._confirmDelete ? t("common.confirm_delete") : k}
            </button>` : k}
      </div>
      ${n.image_url ? D`<img class="hero" src=${n.image_url} alt="" />` : k}
      ${n.description ? D`<p>${n.description}</p>` : k}
      <div class="row muted">
        ${i.prep_time ? D`<span>${t("recipe.prep")}: ${R(t, i.prep_time)}</span>` : k}
        ${i.cook_time ? D`<span>${t("recipe.cook")}: ${R(t, i.cook_time)}</span>` : k}
        ${i.total_time ? D`<span>${t("recipe.total")}: ${R(t, i.total_time)}</span>` : k}
      </div>
      <div class="row section">
        ${n.categories.map((e) => D`<span class="chip">${e.path.join(" › ")}</span>`)}
        ${n.tags.map((e) => D`<span class="chip">#${e}</span>`)}
        ${n.source_url ? D`<a class="btn" href=${n.source_url} target="_blank" rel="noopener noreferrer"
              ><rb-icon .path=${"M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z"}></rb-icon>${t("recipe.source")}</a
            >` : k}
      </div>
      ${this.renderVersions(n)} ${this._showDiff && this._diff ? this.renderDiff() : k}
      <div class="layout section">
        <div class="card">
          <h2>${t("recipe.ingredients")}</h2>
          ${this.renderServings(n)} ${this.renderIngredients(n)}
        </div>
        <div class="card">
          <h2>${t("recipe.steps")}</h2>
          ${this.renderSteps(n)}
        </div>
      </div>
      <div class="layout section">
        <div class="card">${this.renderNotes(n)}</div>
        <div class="card">${this.renderRatings(n)}</div>
      </div>
    `;
	}
	renderVersions(e) {
		let { t } = this.ctx;
		if (e.versions.length < 2) return k;
		let n = e.versions.find((t) => t.id === e.version.id);
		return D`<div class="row section version">
      <label class="muted" for="version">${t("recipe.version")}</label>
      <select
        id="version"
        @change=${(e) => {
			this._versionId = Number(e.target.value), this.load();
		}}
      >
        ${e.versions.map((n) => D`<option value=${String(n.id)} ?selected=${n.id === e.version.id}>
              ${n.label}${n.is_default ? ` (${t("recipe.default")})` : ""}
            </option>`)}
      </select>
      ${n && !n.is_default ? D`<button
            ?disabled=${this._busy}
            @click=${() => this.run(async () => {
			await this.ctx.api.setDefaultVersion(e.id, n.id), await this.load();
		})}
          >
            ${t("recipe.set_default")}
          </button>` : k}
      ${e.version.is_original ? k : D`<button
            @click=${async () => {
			this._showDiff = !this._showDiff, this._showDiff && await this.run(() => this.loadDiff());
		}}
          >
            ${this._showDiff ? t("recipe.hide_diff") : t("recipe.show_diff")}
          </button>`}
    </div>`;
	}
	renderDiff() {
		return D`<div class="card section"><rb-diff .ctx=${this.ctx} .diff=${this._diff}></rb-diff></div>`;
	}
	renderServings(e) {
		let { t } = this.ctx, n = e.version.data.servings;
		return n ? D`<div class="row">
      <span class="stepper">
        <button class="icon" aria-label="−" @click=${() => this.changeServings(-1)}>
          <rb-icon .path=${"M19,13H5V11H19V13Z"}></rb-icon>
        </button>
        <input
          type="number"
          inputmode="decimal"
          min="0.5"
          step="0.5"
          aria-label=${t("recipe.servings")}
          .value=${He("en", n, 2)}
          @change=${(e) => this.setServings(Number(e.target.value))}
        />
        <button class="icon" aria-label="+" @click=${() => this.changeServings(1)}>
          <rb-icon .path=${a}></rb-icon>
        </button>
      </span>
      <span class="muted">${e.version.data.servings_unit ?? t("recipe.servings")}</span>
    </div>` : k;
	}
	notesFor(e, t, n) {
		return e.annotations.filter((e) => e.target_type === t && e.target_index === n).map((e) => D`<div class="note">${e.text}${e.user_name ? D` – ${e.user_name}` : k}</div>`);
	}
	renderIngredients(e) {
		let t = null;
		return D`<ul class="ingredients">
      ${e.version.data.ingredients.map((n, r) => {
			let i = n.group && n.group !== t ? D`<li class="group">${n.group}</li>` : k;
			t = n.group;
			let a = this._checked.has(r);
			return D`${i}
          <li class=${a ? "done" : ""} @click=${() => this.toggle(r)}>
            <input type="checkbox" .checked=${a} aria-label=${n.name} tabindex="-1" />
            <span class="txt">
              ${n.quantity ? D`<span class="qty">${n.quantity}</span> ` : k}${n.name}
              ${n.note ? D`<span class="muted">(${n.note})</span>` : k}
              ${this.notesFor(e, "ingredient", r)}
            </span>
          </li>`;
		})}
    </ul>`;
	}
	renderSteps(e) {
		let { t } = this.ctx, n = null;
		return D`<ol class="steps">
      ${e.version.data.steps.map((r, i) => {
			let a = r.group && r.group !== n ? D`<h3 class="group">${r.group}</h3>` : k;
			return n = r.group, D`${a}
          <li>
            ${r.text}
            ${r.timer_seconds ? D`<div>
                  <button
                    @click=${() => V.start(`${e.title} – ${t("timer.step", { n: i + 1 })}`, e.id, r.timer_seconds)}
                  >
                    <rb-icon .path=${o}></rb-icon>
                    ${t("timer.start", { time: Ve(r.timer_seconds * 1e3) })}
                  </button>
                </div>` : k}
            ${this.notesFor(e, "step", i)}
          </li>`;
		})}
    </ol>`;
	}
	renderNotes(e) {
		let { t } = this.ctx, n = e.annotations.filter((e) => e.target_type === "recipe");
		return D`<h2>${t("recipe.notes")}</h2>
      ${n.map((e) => D`<div class="note">
            ${e.text} <span class="muted">– ${e.user_name ?? ""}, ${z(this.ctx.language, e.created)}</span>
          </div>`)}
      <label for="note">${t("recipe.add_note")}</label>
      <div class="row">
        <input
          id="note"
          class="grow"
          .value=${this._note}
          placeholder=${t("recipe.note_placeholder")}
          @input=${(e) => this._note = e.target.value}
        />
        <button
          class="primary"
          ?disabled=${!this._note.trim() || this._busy}
          @click=${() => this.run(async () => {
			await this.ctx.api.annotate(e.id, this._note.trim()), this._note = "", await this.load();
		})}
        >
          ${t("common.save")}
        </button>
      </div>`;
	}
	renderRatings(e) {
		let { t, language: n } = this.ctx, r = e.stats;
		return D`<h2>${t("recipe.ratings")}</h2>
      ${r.avg_stars === null ? D`<p class="muted">${t("recipe.no_ratings")}</p>` : D`<div class="row">
            <rb-stars .value=${r.avg_stars}></rb-stars>
            <span>${t("recipe.avg", {
			stars: He(n, r.avg_stars),
			n: r.rating_count
		})}</span>
          </div>`}
      <p class="muted">
        ${r.last_cooked ? t("recipe.last_cooked", { date: z(n, r.last_cooked) }) : t("recipe.never_cooked")}
        · ${t("list.cooked", { n: r.cooked_count })}
      </p>
      ${r.per_user.filter((e) => e.avg_stars !== null).map((e) => D`<div class="row muted">
          <span>${e.user_name}</span><rb-stars .value=${e.avg_stars}></rb-stars>
        </div>`)}
      <h3 class="section">${t("recipe.rate")}</h3>
      <rb-stars
        class="pick"
        editable
        .value=${this._stars}
        @change=${(e) => this._stars = e.detail}
      ></rb-stars>
      <label class="row">
        <input
          type="checkbox"
          style="width:22px"
          .checked=${this._cooked}
          @change=${(e) => this._cooked = e.target.checked}
        />
        ${t("recipe.cooked")}
      </label>
      <label for="comment">${t("recipe.comment")}</label>
      <input
        id="comment"
        .value=${this._comment}
        @input=${(e) => this._comment = e.target.value}
      />
      <div class="row section">
        <button class="primary" ?disabled=${this._busy} @click=${() => this.submitRating(e)}>
          ${t("common.save")}
        </button>
      </div>
      ${e.history.length ? D`<h3 class="section">${t("recipe.history")}</h3>
            <ul class="history">
              ${e.history.map((e) => D`<li>
                    <span class="muted">${z(n, e.cooked_at ?? e.created)} · ${e.user_name ?? ""}</span>
                    ${e.stars === null ? k : D`<rb-stars .value=${e.stars}></rb-stars>`}
                    ${e.comment ? D`<div>${e.comment}</div>` : k}
                  </li>`)}
            </ul>` : k}`;
	}
	async submitRating(e) {
		this._stars === null && !this._cooked && !this._comment.trim() ? this.ctx.toast(this.ctx.t("recipe.choose_stars")) : await this.run(async () => {
			await this.ctx.api.rate(e.id, this._stars, this._comment.trim(), this._cooked, e.version.id), this._stars = null, this._comment = "", await this.load();
		}, this.ctx.t("recipe.rated"));
	}
};
ft = pt, ft.properties = {
	ctx: { attribute: !1 },
	recipeId: { type: Number },
	_recipe: { state: !0 },
	_versionId: { state: !0 },
	_servings: { state: !0 },
	_checked: { state: !0 },
	_diff: { state: !0 },
	_showDiff: { state: !0 },
	_error: { state: !0 },
	_stars: { state: !0 },
	_cooked: { state: !0 },
	_comment: { state: !0 },
	_note: { state: !0 },
	_confirmDelete: { state: !0 },
	_busy: { state: !0 }
}, ft.styles = [B, f`
      .top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
      }
      .top h1 {
        margin: 0;
        flex: 1;
      }
      .hero {
        width: 100%;
        max-height: 360px;
        object-fit: cover;
        border-radius: var(--ha-card-border-radius, 12px);
        margin-bottom: 12px;
      }
      .layout {
        display: grid;
        grid-template-columns: minmax(260px, 1fr) 2fr;
        gap: 16px;
        align-items: start;
      }
      @media (max-width: 860px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
      .stepper {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .stepper input {
        width: 80px;
        text-align: center;
      }
      ul.ingredients {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      ul.ingredients li {
        display: flex;
        gap: 10px;
        align-items: flex-start;
        min-height: 44px;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
        cursor: pointer;
      }
      ul.ingredients li.done span.txt {
        text-decoration: line-through;
        opacity: 0.55;
      }
      ul.ingredients input {
        width: 22px;
        min-height: 22px;
        margin-top: 2px;
      }
      .qty {
        font-weight: 500;
        white-space: nowrap;
      }
      ul.ingredients li.group {
        cursor: default;
        border: none;
        min-height: 0;
        padding: 0;
      }
      .group {
        margin: 14px 0 4px;
        font-weight: 500;
        color: var(--secondary-text-color);
      }
      ol.steps {
        padding-left: 1.4em;
        margin: 0;
      }
      ol.steps li {
        padding: 6px 0 12px;
        line-height: 1.55;
        font-size: 1.05rem;
      }
      .note {
        font-size: 0.85rem;
        color: var(--secondary-text-color);
        border-left: 3px solid var(--primary-color);
        padding-left: 8px;
        margin-top: 4px;
      }
      .section {
        margin-top: 16px;
      }
      .history li {
        margin-bottom: 8px;
      }
      rb-stars.pick {
        --rb-star-size: 36px;
      }
      .version select {
        width: auto;
        min-width: 200px;
      }
    `], customElements.get("rb-recipe-view") || customElements.define("rb-recipe-view", pt);
// src/rezeptbuch-panel.ts
var mt, ht = class extends I {
	constructor() {
		super(), this._api = new ze(() => this.hass), this._language = "", this.narrow = !1, this._info = null, this._toast = "", this._ctx = null;
	}
	willUpdate(e) {
		let t = this.hass?.locale?.language ?? this.hass?.language ?? "de";
		this.hass && (!this._ctx || t !== this._language || e.has("_info")) && (this._language = t, this._ctx = {
			hass: this.hass,
			api: this._api,
			t: Ze(t),
			language: t,
			prefix: this.route?.prefix ?? "/rezeptbuch",
			info: this._info,
			go: (e) => et(this.route?.prefix ?? "/rezeptbuch", e),
			toast: (e) => this.showToast(e),
			fail: (e) => Re(e)
		});
	}
	firstUpdated() {
		this._api.info().then((e) => this._info = e).catch(() => this._info = null);
	}
	showToast(e) {
		this._toast = e, clearTimeout(this._toastTimer), this._toastTimer = setTimeout(() => this._toast = "", 4e3);
	}
	toggleMenu() {
		this.dispatchEvent(new Event("hass-toggle-menu", {
			bubbles: !0,
			composed: !0
		}));
	}
	render() {
		let e = this._ctx;
		if (!e) return D``;
		let { t } = e, n = Qe(this.route?.path), r = n.view === "recipe" ? "list" : n.view === "draft" ? "drafts" : n.view, o = (t, n, i) => D`<button aria-current=${r === t ? "page" : "false"} @click=${() => e.go({ view: t })}>
        <rb-icon .path=${n}></rb-icon><span class="label">${i}</span>
      </button>`;
		return D`
      <header>
        ${this.narrow ? D`<button class="icon" aria-label=${t("nav.menu")} @click=${this.toggleMenu}>
              <rb-icon .path=${"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}></rb-icon>
            </button>` : ""}
        <span class="title">${t("app.title")}</span>
        ${o("list", "M19 2L14 6.5V17.5L19 13V2M6.5 5C4.55 5 2.45 5.4 1 6.5V21.16C1 21.41 1.25 21.66 1.5 21.66C1.6 21.66 1.65 21.59 1.75 21.59C3.1 20.94 5.05 20.5 6.5 20.5C8.45 20.5 10.55 20.9 12 22C13.35 21.15 15.8 20.5 17.5 20.5C19.15 20.5 20.85 20.81 22.25 21.56C22.35 21.61 22.4 21.59 22.5 21.59C22.75 21.59 23 21.34 23 21.09V6.5C22.4 6.05 21.75 5.75 21 5.5V19C19.9 18.65 18.7 18.5 17.5 18.5C15.8 18.5 13.35 19.15 12 20V6.5C10.55 5.4 8.45 5 6.5 5Z", t("nav.recipes"))}
        ${o("drafts", i, t("nav.drafts"))} ${o("import", a, t("nav.import"))}
      </header>
      <main>${this.renderView(n, e)}</main>
      <rb-timer-bar .t=${t}></rb-timer-bar>
      ${this._toast ? D`<div class="toast" role="status">${this._toast}</div>` : ""}
    `;
	}
	renderView(e, t) {
		switch (e.view) {
			case "recipe": return D`<rb-recipe-view .ctx=${t} .recipeId=${e.recipeId}></rb-recipe-view>`;
			case "drafts": return D`<rb-drafts-view .ctx=${t}></rb-drafts-view>`;
			case "draft": return D`<rb-draft-editor .ctx=${t} .draftId=${e.draftId}></rb-draft-editor>`;
			case "import": return D`<rb-import-view .ctx=${t}></rb-import-view>`;
			default: return D`<rb-recipe-list .ctx=${t}></rb-recipe-list>`;
		}
	}
};
mt = ht, mt.properties = {
	hass: { attribute: !1 },
	narrow: { type: Boolean },
	route: { attribute: !1 },
	_info: { state: !0 },
	_toast: { state: !0 },
	_ctx: { state: !0 }
}, mt.styles = [B, f`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 100vh;
        background: var(--primary-background-color);
      }
      header {
        position: sticky;
        top: 0;
        z-index: 3;
        display: flex;
        align-items: center;
        gap: 4px;
        min-height: var(--header-height, 56px);
        padding: 0 8px;
        padding-top: env(safe-area-inset-top, 0);
        background: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, var(--text-primary-color, #fff));
      }
      header .title {
        font-size: 1.25rem;
        margin: 0 8px;
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      header button {
        color: inherit;
        background: transparent;
        border-color: transparent;
      }
      header button[aria-current="page"] {
        border-color: currentColor;
      }
      main {
        flex: 1;
        width: 100%;
        max-width: 1400px;
        margin: 0 auto;
        padding: 16px;
        padding-bottom: calc(16px + env(safe-area-inset-bottom, 0));
      }
      rb-timer-bar {
        position: sticky;
        bottom: 0;
        z-index: 3;
        padding-bottom: env(safe-area-inset-bottom, 0);
      }
      .toast {
        position: fixed;
        left: 50%;
        bottom: calc(24px + env(safe-area-inset-bottom, 0));
        transform: translateX(-50%);
        z-index: 5;
        max-width: calc(100% - 32px);
        padding: 12px 18px;
        border-radius: 8px;
        background: var(--primary-text-color);
        color: var(--primary-background-color);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      }
      @media (max-width: 600px) {
        header .label {
          display: none;
        }
        main {
          padding: 10px;
        }
      }
    `], customElements.get("rezeptbuch-panel") || customElements.define("rezeptbuch-panel", ht);
export { ht as RezeptbuchPanel };
